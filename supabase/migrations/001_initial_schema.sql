-- Migration: 001_initial_schema
-- Description: Create users and portfolios tables with RLS policies and Supabase Auth integration
-- Created: 2025-10-08
-- Updated: 2025-10-08 (Refactored to use Supabase Auth)

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- USERS TABLE (Links to auth.users)
-- ============================================================================
-- This table stores custom user data and links to Supabase Auth's auth.users table
-- Authentication is handled by Supabase Auth (email/password stored in auth.users)

CREATE TABLE IF NOT EXISTS users (
    -- id references auth.users, creating a 1-to-1 relationship
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    -- No password_hash! Supabase Auth handles authentication
    experience_level TEXT DEFAULT 'beginner' CHECK (experience_level IN ('beginner', 'intermediate', 'advanced')),
    selected_guru TEXT CHECK (selected_guru IN ('buffett', 'lynch', 'graham', 'dalio')),
    investment_goal TEXT CHECK (investment_goal IN ('retirement', 'wealth', 'income')),
    risk_tolerance TEXT DEFAULT 'medium' CHECK (risk_tolerance IN ('low', 'medium', 'high')),
    age INTEGER CHECK (age >= 18 AND age <= 120),
    investment_timeline INTEGER CHECK (investment_timeline > 0),
    learning_progress INTEGER DEFAULT 0 CHECK (learning_progress >= 0 AND learning_progress <= 100),
    onboarding_completed BOOLEAN DEFAULT false,
    preferred_mode TEXT DEFAULT 'beginner' CHECK (preferred_mode IN ('beginner', 'advanced')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add index on email for faster lookups
CREATE INDEX idx_users_email ON users(email);

-- Add index on experience_level for filtering
CREATE INDEX idx_users_experience_level ON users(experience_level);

-- ============================================================================
-- PORTFOLIOS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    stocks JSONB NOT NULL DEFAULT '[]'::jsonb,
    total_value NUMERIC(15, 2) DEFAULT 0.00,
    optimization_method TEXT CHECK (optimization_method IN ('equal', 'markowitz', 'risk_parity', 'max_sharpe', 'hrp', 'black_litterman')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add index on user_id for faster queries
CREATE INDEX idx_portfolios_user_id ON portfolios(user_id);

-- Add index on created_at for sorting
CREATE INDEX idx_portfolios_created_at ON portfolios(created_at DESC);

-- ============================================================================
-- UPDATED_AT TRIGGER FUNCTION
-- ============================================================================

-- Create a function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to users table
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to portfolios table
CREATE TRIGGER update_portfolios_updated_at
    BEFORE UPDATE ON portfolios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Enable RLS on portfolios table
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- USERS TABLE RLS POLICIES
-- ============================================================================

-- Policy: Users can view their own profile
CREATE POLICY "Users can view own profile"
    ON users
    FOR SELECT
    USING (auth.uid() = id);

-- Policy: Users can update their own profile
CREATE POLICY "Users can update own profile"
    ON users
    FOR UPDATE
    USING (auth.uid() = id);

-- Policy: Users can insert their own profile (for registration)
CREATE POLICY "Users can insert own profile"
    ON users
    FOR INSERT
    WITH CHECK (auth.uid() = id);

-- Policy: Users can delete their own profile
CREATE POLICY "Users can delete own profile"
    ON users
    FOR DELETE
    USING (auth.uid() = id);

-- ============================================================================
-- PORTFOLIOS TABLE RLS POLICIES
-- ============================================================================

-- Policy: Users can view their own portfolios
CREATE POLICY "Users can view own portfolios"
    ON portfolios
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can insert their own portfolios
CREATE POLICY "Users can insert own portfolios"
    ON portfolios
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own portfolios
CREATE POLICY "Users can update own portfolios"
    ON portfolios
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Policy: Users can delete their own portfolios
CREATE POLICY "Users can delete own portfolios"
    ON portfolios
    FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE users IS 'Stores user accounts with profile information and investment preferences';
COMMENT ON TABLE portfolios IS 'Stores user investment portfolios with stocks and optimization settings';

COMMENT ON COLUMN users.experience_level IS 'User investment experience: beginner, intermediate, or advanced';
COMMENT ON COLUMN users.selected_guru IS 'Preferred investment guru: buffett, lynch, graham, or dalio';
COMMENT ON COLUMN users.investment_goal IS 'Primary investment goal: retirement, wealth, or income';
COMMENT ON COLUMN users.risk_tolerance IS 'Risk tolerance level: low, medium, or high';
COMMENT ON COLUMN users.learning_progress IS 'Progress through educational content (0-100)';
COMMENT ON COLUMN users.preferred_mode IS 'UI mode preference: beginner (guided) or advanced (full features)';

COMMENT ON COLUMN portfolios.stocks IS 'JSONB array of stock holdings: [{ticker, shares, price, ...}]';
COMMENT ON COLUMN portfolios.optimization_method IS 'Portfolio optimization algorithm used';

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Grant authenticated users access to their own data
GRANT SELECT, INSERT, UPDATE, DELETE ON users TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON portfolios TO authenticated;

-- ============================================================================
-- AUTO-CREATE USER PROFILE ON SIGNUP
-- ============================================================================
-- This trigger automatically creates a user profile in public.users when
-- someone signs up via Supabase Auth (auth.users table)

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'name', NEW.email)
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to call handle_new_user() when a new user signs up
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

COMMENT ON FUNCTION public.handle_new_user() IS 'Automatically creates user profile in public.users when auth.users record is created';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Migration 001_initial_schema completed successfully
-- Now supports Supabase Auth with automatic profile creation

