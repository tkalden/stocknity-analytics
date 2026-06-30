#!/usr/bin/env python3
"""
Main entry point for the Flask application
"""
import os
from .__init__ import create_app

app = create_app()

if __name__ == '__main__':
    # Use environment variable for port, default to 5001
    port = int(os.environ.get('PORT', 5001))
    # Disable debug mode in production
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)