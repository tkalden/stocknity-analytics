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
SUPABASE_KEY=your-anon-key-here

# Your Supabase service role key (KEEP SECRET - server-side only)
# Find this in: Supabase Dashboard → Settings → API → Project API keys → service_role
# WARNING: This key bypasses Row Level Security. Never expose it to clients!
SUPABASE_SERVICE_KEY=your-service-role-key-here
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

```python
from backend.config.supabase_client import supabase

# The client automatically loads from environment variables
# No need to manually configure
```

