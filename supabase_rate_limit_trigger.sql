
-- ============================================
-- POSTGRESQL TRIGGER FOR RATE LIMITING
-- Enforces security at database level
-- Cannot be bypassed by users
-- ============================================

-- Function to check rate limits before inserting
CREATE OR REPLACE FUNCTION check_verification_rate_limit()
RETURNS TRIGGER AS $$
DECLARE
    user_request_count INTEGER;
    pattern_request_count INTEGER;
    global_request_count INTEGER;
    last_request_time TIMESTAMP;
BEGIN
    -- ==========================================
    -- RATE LIMIT 1: Per-User Rate Limit
    -- Max 3 requests per hour per user
    -- ==========================================
    SELECT COUNT(*), MAX(created_at)
    INTO user_request_count, last_request_time
    FROM verify_requests
    WHERE user_id = NEW.user_id
    AND created_at > NOW() - INTERVAL '1 hour';
    
    IF user_request_count >= 3 THEN
        RAISE EXCEPTION 'Rate limit exceeded: Maximum 3 verification requests per hour. Please try again later.'
        USING ERRCODE = '42501';
    END IF;
    
    -- ==========================================
    -- RATE LIMIT 2: Duplicate Request Prevention
    -- No duplicate requests within 5 minutes
    -- ==========================================
    IF last_request_time IS NOT NULL AND last_request_time > NOW() - INTERVAL '5 minutes' THEN
        RAISE EXCEPTION 'Rate limit exceeded: Please wait at least 5 minutes between verification requests.'
        USING ERRCODE = '42501';
    END IF;
    
    -- ==========================================
    -- RATE LIMIT 3: Pattern Validation
    -- Pattern must match format (first6)...(last4)
    -- ==========================================
    IF NEW.pattern !~ '^[0-9a-zA-Z]{6,}\.\.\.[0-9a-zA-Z]{4,}$' THEN
        RAISE EXCEPTION 'Invalid pattern format: Must be in format (first6)...(last4)'
        USING ERRCODE = '42501';
    END IF;
    
    -- ==========================================
    -- RATE LIMIT 4: Global Rate Limit
    -- Max 100 total requests per minute (DDoS protection)
    -- ==========================================
    SELECT COUNT(*)
    INTO global_request_count
    FROM verify_requests
    WHERE created_at > NOW() - INTERVAL '1 minute';
    
    IF global_request_count >= 100 THEN
        RAISE EXCEPTION 'System overload: Too many verification requests. Please try again in a minute.'
        USING ERRCODE = '42501';
    END IF;
    
    -- ==========================================
    -- All checks passed - allow insert
    -- ==========================================
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS verify_requests_rate_limit ON verify_requests;

-- Create trigger that runs BEFORE INSERT
CREATE TRIGGER verify_requests_rate_limit
BEFORE INSERT ON verify_requests
FOR EACH ROW
EXECUTE FUNCTION check_verification_rate_limit();

-- ==========================================
-- CLEANUP FUNCTION (Optional)
-- Run periodically to delete old requests
-- ==========================================
CREATE OR REPLACE FUNCTION cleanup_old_verify_requests()
RETURNS void AS $$
BEGIN
    DELETE FROM verify_requests
    WHERE created_at < NOW() - INTERVAL '30 days'
    AND status IN ('approved', 'denied');
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- COMMENTS FOR DOCUMENTATION
-- ==========================================
COMMENT ON FUNCTION check_verification_rate_limit() IS 'Enforces rate limits and validation for verification requests. Cannot be bypassed by client code.';
COMMENT ON TRIGGER verify_requests_rate_limit ON verify_requests IS 'Validates and rate-limits verification requests before insertion';
