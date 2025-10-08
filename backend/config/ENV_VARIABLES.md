# Environment Variables Configuration

This document lists all required environment variables for the Stocknity backend.

## Required Environment Variables

### Supabase Configuration

```bash
# Your Supabase project URL
# Find this in: Supabase Dashboard → Settings → API → Project URL
SUPABASE_URL=https://your-project-id.supabase.co

# Your Supabase anon/public key (safe for client-side use)
# Find this in: Supabase Dashboard → Settings → API → Project API keys → anon/public
# This key is used for both backend and frontend authentication
SUPABASE_KEY=your-anon-key-here
```

### Supabase Auth Configuration

Supabase Auth is automatically configured with your Supabase project. Additional auth settings:

```bash
# Optional: JWT Secret (usually not needed, Supabase manages this)
# Only needed for custom JWT verification
# SUPABASE_JWT_SECRET=your-jwt-secret

# Optional: Redirect URL for OAuth and email confirmations
# Set this in Supabase Dashboard → Authentication → URL Configuration
# Example: https://your-app.vercel.app/auth/callback
```

### Redis Configuration (Vercel KV)

```bash
# Redis connection URL from Vercel KV
# Find this in: Vercel Dashboard → Storage → Your KV Store → .env.local
REDIS_URL=redis://default:your-redis-password@your-redis-host.kv.vercel-storage.com:port
```

### API Keys for Data Sources

```bash
# Alpha Vantage API Key (for stock data)
# Get free key at: https://www.alphavantage.co/support/#api-key
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key

# Financial Modeling Prep API Key (optional)
FMP_API_KEY=your-fmp-key
```

### Flask Configuration

```bash
FLASK_SECRET_KEY=your-super-secret-key-change-this-in-production
FLASK_ENV=development
FLASK_DEBUG=True
```

### CORS Configuration

```bash
# Allowed origins for CORS (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000
```

### Logging

```bash
LOG_LEVEL=INFO
```

## Setup Instructions

1. **Create `.env` file:**
   ```bash
   cd /Users/tenzinkalden/projects/stock-portfolio
   touch .env
   ```

2. **Copy the variables above into your `.env` file**

3. **Replace placeholder values** with your actual credentials

4. **For Vercel deployment:**
   - Add these in Vercel Dashboard → Settings → Environment Variables
   - Vercel will inject them at runtime

5. **Verify `.env` is in `.gitignore`** (it should be by default)

## Usage in Code

### Database Operations
```python
from backend.config.supabase_client import get_user_by_email, create_portfolio

# The client automatically loads from environment variables
user = await get_user_by_email("user@example.com")
```

### Authentication Operations
```python
from backend.config.supabase_client import sign_up, sign_in, sign_out

# Sign up a new user (creates auth.users + public.users automatically)
result = await sign_up(
    email="user@stocknity.com",
    password="secure_password",
    user_data={'name': 'John Doe'}
)

# Sign in
session = await sign_in("user@stocknity.com", "secure_password")
access_token = session['session']['access_token']

# Sign out
await sign_out()
```

## Authentication Architecture

Stocknity uses **Supabase Auth** for authentication, which provides:

✅ **Security:** Battle-tested auth with automatic security patches  
✅ **Features:** Email verification, password reset, OAuth, magic links  
✅ **JWT Tokens:** Automatic token management with refresh  
✅ **RLS Integration:** Row Level Security enforced automatically  
✅ **No Custom Auth Code:** No need to build login/signup/logout routes  

### How It Works

1. **User signs up** → Creates record in `auth.users` (Supabase managed)
2. **Trigger fires** → Automatically creates profile in `public.users` (your custom data)
3. **User logs in** → Gets JWT token with `user_id`
4. **RLS enforces access** → Queries automatically filtered by `auth.uid()`

### Data Structure

```
auth.users (Supabase managed)
├── id (UUID)
├── email
├── encrypted_password
├── email_confirmed_at
└── created_at

public.users (Your custom data)
├── id (UUID) → references auth.users.id
├── name
├── experience_level
├── selected_guru
└── ... (all your custom fields)
```

