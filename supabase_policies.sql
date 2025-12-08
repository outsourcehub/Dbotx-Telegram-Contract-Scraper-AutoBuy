
-- ============================================
-- ROW LEVEL SECURITY POLICIES
-- NOTE: Rate limiting is now handled by PostgreSQL triggers
-- These policies are kept for basic access control only
-- ============================================

-- Enable RLS on verify_requests
ALTER TABLE verify_requests ENABLE ROW LEVEL SECURITY;

-- Allow service_role to do everything (VerifyAddy bot needs full access)
CREATE POLICY "Service role has full access to verify_requests"
ON verify_requests
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Allow service_role to do everything on wallet_patterns
CREATE POLICY "Service role has full access to wallet_patterns"
ON wallet_patterns
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Note: Public bot uses service_role key
-- Security is enforced by PostgreSQL triggers (see supabase_rate_limit_trigger.sql)
-- Triggers cannot be bypassed by users since they run server-side
