from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import secrets
from functools import wraps
import logging

# Paths exempt from the internal-secret gate (health check + root probe).
_PUBLIC_PATHS = {'/api/health', '/'}


def create_app():
    app = Flask(__name__)

    # Security Configuration
    configure_security(app)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    if not app.config['SECRET_KEY']:
        # Generate a secure key if not provided
        app.config['SECRET_KEY'] = secrets.token_hex(32)
        logging.warning("SECRET_KEY not set - generated temporary key. Set SECRET_KEY environment variable for production.")

    app.config['REDIS_HOST'] = os.environ.get('REDIS_HOST', 'localhost')
    app.config['REDIS_PORT'] = int(os.environ.get('REDIS_PORT', 6379))
    app.config['REDIS_DB'] = int(os.getenv('REDIS_DB', 0))

    # Security middleware
    setup_security_middleware(app)

    # Internal secret — this is the SOLE access control. Flask must only be
    # reachable via the Spring gateway, which injects X-Internal-Secret on
    # every proxied request. There is no Flask-side user auth anymore.
    internal_secret = os.environ.get('INTERNAL_SECRET')
    is_production = os.environ.get('FLASK_ENV') == 'production'

    if not internal_secret:
        if is_production:
            # Fail fast: a production deployment without a shared secret would
            # be open to the world. The gateway must set INTERNAL_SECRET.
            raise RuntimeError(
                "INTERNAL_SECRET is unset in production. Flask is only reachable "
                "via the Spring gateway and must require X-Internal-Secret. "
                "Set INTERNAL_SECRET to the same value the gateway injects."
            )
        logging.warning(
            "INTERNAL_SECRET is unset — internal-secret gate is DISABLED. "
            "This is acceptable for local development only. In production this "
            "would raise a RuntimeError."
        )

    @app.before_request
    def require_internal_secret():
        if request.path in _PUBLIC_PATHS:
            return None
        if not internal_secret:
            # Non-production with no secret configured: allow through (dev only).
            return None
        if request.headers.get('X-Internal-Secret') != internal_secret:
            return jsonify({'error': 'Forbidden'}), 403

    # Import and register blueprints
    from src.api.auth import auth
    app.register_blueprint(auth)

    from src.api.main import main
    app.register_blueprint(main)

    return app

def configure_security(app):
    """Configure security settings.

    There are no server-side sessions: auth was retired and access control is
    handled solely by the X-Internal-Secret gate. Only response security
    headers are configured here.
    """
    # Security headers
    if os.environ.get('ENABLE_SECURITY_HEADERS', 'true').lower() == 'true':
        @app.after_request
        def add_security_headers(response):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Content Security Policy
            csp_parts = []
            default_src = os.environ.get('CSP_DEFAULT_SRC', "'self'")
            script_src = os.environ.get('CSP_SCRIPT_SRC', "'self' 'unsafe-inline'")
            style_src = os.environ.get('CSP_STYLE_SRC', "'self' 'unsafe-inline'")
            img_src = os.environ.get('CSP_IMG_SRC', "'self' data: https:")
            connect_src = os.environ.get('CSP_CONNECT_SRC', "'self' https:")
            
            csp_parts.append(f"default-src {default_src}")
            csp_parts.append(f"script-src {script_src}")
            csp_parts.append(f"style-src {style_src}")
            csp_parts.append(f"img-src {img_src}")
            csp_parts.append(f"connect-src {connect_src}")
            
            response.headers['Content-Security-Policy'] = '; '.join(csp_parts)
            return response

def configure_cors(app):
    """Configure CORS with environment-based origins and dynamic Vercel URL detection"""
    
    # Base allowed origins
    base_origins = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:3001')
    origins = [origin.strip() for origin in base_origins.split(',')]
    
    # Add Vercel UI URL if provided
    vercel_ui_url = os.environ.get('VERCEL_UI_URL')
    if vercel_ui_url:
        origins.append(vercel_ui_url.strip())
    
    # Add Vercel preview URLs pattern (for PR deployments)
    vercel_preview_pattern = os.environ.get('VERCEL_PREVIEW_PATTERN', 'https://*.vercel.app')
    if vercel_preview_pattern:
        origins.append(vercel_preview_pattern)
    
    # Add production Vercel URL pattern
    vercel_production_pattern = os.environ.get('VERCEL_PRODUCTION_PATTERN', 'https://stocknity-ui.vercel.app')
    if vercel_production_pattern:
        origins.append(vercel_production_pattern)
    
    # Remove duplicates and filter empty strings
    origins = list(set([origin for origin in origins if origin]))
    
    logging.info(f"Configured CORS origins: {origins}")
    
    # Add Vercel-specific CORS headers
    CORS(app, origins=origins, supports_credentials=True, 
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

def setup_security_middleware(app):
    """Setup security middleware"""
    # Rate limiting
    from collections import defaultdict
    import time
    
    request_counts = defaultdict(list)
    
    def rate_limit(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = time.time()
            
            # Clean old requests
            request_counts[client_ip] = [req_time for req_time in request_counts[client_ip] 
                                       if current_time - req_time < 60]
            
            # Check rate limits
            requests_per_minute = int(os.environ.get('RATE_LIMIT_REQUESTS_PER_MINUTE', 100))
            requests_per_hour = int(os.environ.get('RATE_LIMIT_REQUESTS_PER_HOUR', 1000))
            
            if len(request_counts[client_ip]) >= requests_per_minute:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            # Add current request
            request_counts[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    
    # Apply rate limiting to all API routes
    for endpoint in app.view_functions:
        if endpoint.startswith('api.'):
            app.view_functions[endpoint] = rate_limit(app.view_functions[endpoint])