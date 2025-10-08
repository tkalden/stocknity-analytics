"""
Supabase Client Configuration

This module provides a singleton Supabase client and helper functions
for database operations including user and portfolio management.
"""

import os
import logging
from typing import Optional, Dict, List, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase credentials from environment
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize supabase client as None (will be created on first use)
supabase: Optional[Client] = None


def _get_supabase_client() -> Client:
    """
    Get or create the Supabase client (lazy initialization).
    
    This allows the module to be imported even if environment variables
    aren't set, which is useful for testing and development.
    
    Returns:
        Initialized Supabase client
        
    Raises:
        ValueError: If environment variables are not set
    """
    global supabase
    
    if supabase is not None:
        return supabase
    
    # Validate required environment variables
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "Missing required environment variables: SUPABASE_URL and SUPABASE_KEY must be set. "
            "See backend/config/ENV_VARIABLES.md for setup instructions."
        )
    
    # Create singleton Supabase client
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Supabase client initialized successfully")
        return supabase
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase client: {e}")
        raise


# Initialize client immediately if credentials are available
# This maintains backwards compatibility for code that expects `supabase` to be initialized
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = _get_supabase_client()
    except Exception as e:
        logger.warning(f"⚠️ Supabase client will be initialized on first use: {e}")


# ============================================================================
# USER OPERATIONS
# ============================================================================

async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user by their email address.
    
    Args:
        email: User's email address
        
    Returns:
        User dictionary if found, None otherwise
        
    Raises:
        Exception: If database query fails
        
    Example:
        >>> user = await get_user_by_email("test@stocknity.com")
        >>> if user:
        ...     print(f"Found user: {user['name']}")
    """
    try:
        response = supabase.table('users').select('*').eq('email', email).execute()
        
        if response.data and len(response.data) > 0:
            logger.info(f"✅ User found: {email}")
            return response.data[0]
        
        logger.warning(f"⚠️ User not found: {email}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error fetching user by email {email}: {e}")
        raise


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user by their ID.
    
    Args:
        user_id: User's UUID
        
    Returns:
        User dictionary if found, None otherwise
        
    Raises:
        Exception: If database query fails
        
    Example:
        >>> user = await get_user_by_id("abc123-...")
        >>> if user:
        ...     print(f"User: {user['name']}")
    """
    try:
        response = supabase.table('users').select('*').eq('id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            logger.info(f"✅ User found by ID: {user_id}")
            return response.data[0]
        
        logger.warning(f"⚠️ User not found by ID: {user_id}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error fetching user by ID {user_id}: {e}")
        raise


async def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new user in the database.
    
    Args:
        user_data: Dictionary containing user fields (email, name, password_hash, etc.)
        
    Returns:
        Created user dictionary with ID
        
    Raises:
        Exception: If user creation fails (e.g., duplicate email)
        
    Example:
        >>> user_data = {
        ...     'email': 'new@stocknity.com',
        ...     'name': 'New User',
        ...     'password_hash': 'hashed_password',
        ...     'experience_level': 'beginner'
        ... }
        >>> new_user = await create_user(user_data)
        >>> print(f"Created user with ID: {new_user['id']}")
    """
    try:
        response = supabase.table('users').insert(user_data).execute()
        
        if response.data and len(response.data) > 0:
            created_user = response.data[0]
            logger.info(f"✅ User created: {created_user['email']} (ID: {created_user['id']})")
            return created_user
        
        raise Exception("User creation returned no data")
        
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}")
        raise


async def update_user(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing user's information.
    
    Args:
        user_id: User's UUID
        updates: Dictionary of fields to update
        
    Returns:
        Updated user dictionary
        
    Raises:
        Exception: If update fails or user not found
        
    Example:
        >>> updates = {
        ...     'learning_progress': 85,
        ...     'preferred_mode': 'advanced'
        ... }
        >>> updated_user = await update_user("abc123-...", updates)
        >>> print(f"Updated user: {updated_user['name']}")
    """
    try:
        response = supabase.table('users').update(updates).eq('id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            updated_user = response.data[0]
            logger.info(f"✅ User updated: {user_id}")
            return updated_user
        
        raise Exception(f"User not found or update failed: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error updating user {user_id}: {e}")
        raise


async def delete_user(user_id: str) -> bool:
    """
    Delete a user from the database.
    
    Note: This will CASCADE delete all associated portfolios due to the
    foreign key constraint in the database schema.
    
    Args:
        user_id: User's UUID
        
    Returns:
        True if deletion was successful
        
    Raises:
        Exception: If deletion fails
        
    Example:
        >>> success = await delete_user("abc123-...")
        >>> if success:
        ...     print("User deleted successfully")
    """
    try:
        response = supabase.table('users').delete().eq('id', user_id).execute()
        logger.info(f"✅ User deleted: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error deleting user {user_id}: {e}")
        raise


# ============================================================================
# PORTFOLIO OPERATIONS
# ============================================================================

async def get_user_portfolios(user_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all portfolios belonging to a user.
    
    Args:
        user_id: User's UUID
        
    Returns:
        List of portfolio dictionaries (may be empty)
        
    Raises:
        Exception: If database query fails
        
    Example:
        >>> portfolios = await get_user_portfolios("abc123-...")
        >>> print(f"User has {len(portfolios)} portfolios")
        >>> for portfolio in portfolios:
        ...     print(f"  - {portfolio['name']}: ${portfolio['total_value']}")
    """
    try:
        response = supabase.table('portfolios').select('*').eq('user_id', user_id).execute()
        
        portfolios = response.data if response.data else []
        logger.info(f"✅ Found {len(portfolios)} portfolios for user {user_id}")
        return portfolios
        
    except Exception as e:
        logger.error(f"❌ Error fetching portfolios for user {user_id}: {e}")
        raise


async def get_portfolio_by_id(portfolio_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a portfolio by its ID.
    
    Args:
        portfolio_id: Portfolio's UUID
        
    Returns:
        Portfolio dictionary if found, None otherwise
        
    Raises:
        Exception: If database query fails
        
    Example:
        >>> portfolio = await get_portfolio_by_id("xyz789-...")
        >>> if portfolio:
        ...     print(f"Portfolio: {portfolio['name']}")
    """
    try:
        response = supabase.table('portfolios').select('*').eq('id', portfolio_id).execute()
        
        if response.data and len(response.data) > 0:
            logger.info(f"✅ Portfolio found: {portfolio_id}")
            return response.data[0]
        
        logger.warning(f"⚠️ Portfolio not found: {portfolio_id}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error fetching portfolio {portfolio_id}: {e}")
        raise


async def create_portfolio(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new portfolio for a user.
    
    Args:
        portfolio_data: Dictionary containing portfolio fields (user_id, name, stocks, etc.)
        
    Returns:
        Created portfolio dictionary with ID
        
    Raises:
        Exception: If portfolio creation fails
        
    Example:
        >>> portfolio_data = {
        ...     'user_id': 'abc123-...',
        ...     'name': 'My First Portfolio',
        ...     'stocks': [
        ...         {'ticker': 'AAPL', 'shares': 10, 'price': 150.00}
        ...     ],
        ...     'total_value': 1500.00
        ... }
        >>> new_portfolio = await create_portfolio(portfolio_data)
        >>> print(f"Created portfolio: {new_portfolio['id']}")
    """
    try:
        response = supabase.table('portfolios').insert(portfolio_data).execute()
        
        if response.data and len(response.data) > 0:
            created_portfolio = response.data[0]
            logger.info(f"✅ Portfolio created: {created_portfolio['name']} (ID: {created_portfolio['id']})")
            return created_portfolio
        
        raise Exception("Portfolio creation returned no data")
        
    except Exception as e:
        logger.error(f"❌ Error creating portfolio: {e}")
        raise


async def update_portfolio(portfolio_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing portfolio.
    
    Args:
        portfolio_id: Portfolio's UUID
        updates: Dictionary of fields to update
        
    Returns:
        Updated portfolio dictionary
        
    Raises:
        Exception: If update fails or portfolio not found
        
    Example:
        >>> updates = {
        ...     'stocks': [...],
        ...     'total_value': 2500.00
        ... }
        >>> updated_portfolio = await update_portfolio("xyz789-...", updates)
    """
    try:
        response = supabase.table('portfolios').update(updates).eq('id', portfolio_id).execute()
        
        if response.data and len(response.data) > 0:
            updated_portfolio = response.data[0]
            logger.info(f"✅ Portfolio updated: {portfolio_id}")
            return updated_portfolio
        
        raise Exception(f"Portfolio not found or update failed: {portfolio_id}")
        
    except Exception as e:
        logger.error(f"❌ Error updating portfolio {portfolio_id}: {e}")
        raise


async def delete_portfolio(portfolio_id: str) -> bool:
    """
    Delete a portfolio from the database.
    
    Args:
        portfolio_id: Portfolio's UUID
        
    Returns:
        True if deletion was successful
        
    Raises:
        Exception: If deletion fails
        
    Example:
        >>> success = await delete_portfolio("xyz789-...")
        >>> if success:
        ...     print("Portfolio deleted successfully")
    """
    try:
        response = supabase.table('portfolios').delete().eq('id', portfolio_id).execute()
        logger.info(f"✅ Portfolio deleted: {portfolio_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error deleting portfolio {portfolio_id}: {e}")
        raise


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def count_user_portfolios(user_id: str) -> int:
    """
    Count the number of portfolios a user has.
    
    This is useful for checking graduation eligibility criteria.
    
    Args:
        user_id: User's UUID
        
    Returns:
        Number of portfolios
        
    Example:
        >>> count = await count_user_portfolios("abc123-...")
        >>> print(f"User has {count} portfolios")
    """
    try:
        portfolios = await get_user_portfolios(user_id)
        return len(portfolios)
    except Exception as e:
        logger.error(f"❌ Error counting portfolios for user {user_id}: {e}")
        raise


async def health_check() -> Dict[str, Any]:
    """
    Check if Supabase connection is working.
    
    Returns:
        Dictionary with connection status and details
        
    Example:
        >>> status = await health_check()
        >>> if status['connected']:
        ...     print("Supabase is connected!")
    """
    try:
        # Try a simple query to test connection
        response = supabase.table('users').select('count', count='exact').limit(0).execute()
        
        return {
            'connected': True,
            'url': SUPABASE_URL,
            'status': 'healthy'
        }
    except Exception as e:
        logger.error(f"❌ Supabase health check failed: {e}")
        return {
            'connected': False,
            'url': SUPABASE_URL,
            'status': 'unhealthy',
            'error': str(e)
        }


# ============================================================================
# AUTHENTICATION OPERATIONS (Supabase Auth)
# ============================================================================

async def sign_up(email: str, password: str, user_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Sign up a new user using Supabase Auth.
    
    This creates a user in auth.users and automatically triggers the creation
    of a profile in public.users via the handle_new_user() trigger.
    
    Args:
        email: User's email address
        password: User's password (will be hashed by Supabase)
        user_data: Optional dictionary of additional user metadata (e.g., {'name': 'John Doe'})
        
    Returns:
        Dictionary with user data and session info
        
    Raises:
        Exception: If signup fails (e.g., email already exists, weak password)
        
    Example:
        >>> result = await sign_up(
        ...     email="user@stocknity.com",
        ...     password="securePassword123",
        ...     user_data={'name': 'John Doe'}
        ... )
        >>> print(f"User created: {result['user']['id']}")
    """
    try:
        client = _get_supabase_client()
        
        # Prepare signup data
        signup_data = {
            "email": email,
            "password": password
        }
        
        # Add user metadata if provided
        if user_data:
            signup_data["options"] = {"data": user_data}
        
        # Sign up using Supabase Auth
        response = client.auth.sign_up(signup_data)
        
        if response.user:
            logger.info(f"✅ User signed up: {email} (ID: {response.user.id})")
            return {
                'user': response.user.__dict__,
                'session': response.session.__dict__ if response.session else None
            }
        
        raise Exception("Signup failed: No user returned")
        
    except Exception as e:
        logger.error(f"❌ Error signing up user {email}: {e}")
        raise


async def sign_in(email: str, password: str) -> Dict[str, Any]:
    """
    Sign in an existing user using Supabase Auth.
    
    Args:
        email: User's email address
        password: User's password
        
    Returns:
        Dictionary with user data and session info (including JWT tokens)
        
    Raises:
        Exception: If login fails (wrong credentials, unverified email, etc.)
        
    Example:
        >>> result = await sign_in("user@stocknity.com", "password123")
        >>> session = result['session']
        >>> access_token = session['access_token']
        >>> # Use access_token for authenticated API requests
    """
    try:
        client = _get_supabase_client()
        
        # Sign in using Supabase Auth
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user and response.session:
            logger.info(f"✅ User signed in: {email}")
            return {
                'user': response.user.__dict__,
                'session': response.session.__dict__
            }
        
        raise Exception("Login failed: Invalid credentials")
        
    except Exception as e:
        logger.error(f"❌ Error signing in user {email}: {e}")
        raise


async def sign_out() -> bool:
    """
    Sign out the current user.
    
    Returns:
        True if sign out was successful
        
    Example:
        >>> success = await sign_out()
        >>> if success:
        ...     print("User signed out")
    """
    try:
        client = _get_supabase_client()
        client.auth.sign_out()
        logger.info("✅ User signed out")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error signing out: {e}")
        raise


async def get_current_user(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get the currently authenticated user from their JWT token.
    
    Args:
        access_token: JWT access token from session
        
    Returns:
        User dictionary if token is valid, None otherwise
        
    Example:
        >>> user = await get_current_user(session['access_token'])
        >>> if user:
        ...     print(f"Current user: {user['email']}")
    """
    try:
        client = _get_supabase_client()
        
        # Get user from token
        response = client.auth.get_user(access_token)
        
        if response.user:
            logger.info(f"✅ Retrieved current user: {response.user.email}")
            return response.user.__dict__
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error getting current user: {e}")
        return None


async def reset_password_email(email: str) -> bool:
    """
    Send a password reset email to the user.
    
    Args:
        email: User's email address
        
    Returns:
        True if email was sent successfully
        
    Raises:
        Exception: If sending email fails
        
    Example:
        >>> success = await reset_password_email("user@stocknity.com")
        >>> if success:
        ...     print("Password reset email sent")
    """
    try:
        client = _get_supabase_client()
        
        # Send password reset email
        client.auth.reset_password_email(email)
        logger.info(f"✅ Password reset email sent to: {email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error sending password reset email to {email}: {e}")
        raise


async def update_password(access_token: str, new_password: str) -> bool:
    """
    Update user's password (requires current session token).
    
    Args:
        access_token: JWT access token from current session
        new_password: New password to set
        
    Returns:
        True if password was updated successfully
        
    Raises:
        Exception: If update fails
        
    Example:
        >>> success = await update_password(session['access_token'], "newPassword123")
        >>> if success:
        ...     print("Password updated")
    """
    try:
        client = _get_supabase_client()
        
        # Update password
        response = client.auth.update_user(
            access_token,
            {"password": new_password}
        )
        
        if response.user:
            logger.info(f"✅ Password updated for user: {response.user.email}")
            return True
        
        raise Exception("Password update failed")
        
    except Exception as e:
        logger.error(f"❌ Error updating password: {e}")
        raise


async def verify_email(token: str) -> Dict[str, Any]:
    """
    Verify user's email using verification token from email link.
    
    Args:
        token: Verification token from email link
        
    Returns:
        Dictionary with user data and session
        
    Raises:
        Exception: If verification fails
        
    Example:
        >>> result = await verify_email(token_from_email_link)
        >>> if result:
        ...     print("Email verified!")
    """
    try:
        client = _get_supabase_client()
        
        # Verify email
        response = client.auth.verify_otp({
            "token": token,
            "type": "email"
        })
        
        if response.user:
            logger.info(f"✅ Email verified for user: {response.user.email}")
            return {
                'user': response.user.__dict__,
                'session': response.session.__dict__ if response.session else None
            }
        
        raise Exception("Email verification failed")
        
    except Exception as e:
        logger.error(f"❌ Error verifying email: {e}")
        raise


# Export commonly used functions
__all__ = [
    'supabase',
    # User operations
    'get_user_by_email',
    'get_user_by_id',
    'create_user',
    'update_user',
    'delete_user',
    # Portfolio operations
    'get_user_portfolios',
    'get_portfolio_by_id',
    'create_portfolio',
    'update_portfolio',
    'delete_portfolio',
    # Utility functions
    'count_user_portfolios',
    'health_check',
    # Authentication operations
    'sign_up',
    'sign_in',
    'sign_out',
    'get_current_user',
    'reset_password_email',
    'update_password',
    'verify_email'
]

