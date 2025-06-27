-- Phase 4: Database Schema Migration
-- This migration adds the missing tables and columns that caused the Supabase errors

-- First, check if tables exist and create them if they don't
DO $$
BEGIN

-- Create processed_content table if it doesn't exist
IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'processed_content') THEN
    CREATE TABLE processed_content (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        processing_date DATE NOT NULL,
        edition VARCHAR NOT NULL, -- 'daily', 'weekly', etc.
        content_type VARCHAR NOT NULL, -- 'newsletter', 'summary', etc.
        title TEXT NOT NULL,
        lead_paragraph TEXT,
        articles_count INTEGER NOT NULL DEFAULT 0,
        multi_source_topics INTEGER DEFAULT 0,
        content_md TEXT NOT NULL, -- Generated markdown content
        metadata JSONB DEFAULT '{}', -- Additional metadata (topics, sources, etc.)
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        
        -- Composite unique constraint
        UNIQUE(processing_date, edition, content_type)
    );
    
    -- Create indexes
    CREATE INDEX idx_processed_content_date ON processed_content(processing_date);
    CREATE INDEX idx_processed_content_edition ON processed_content(edition);
    
    -- Enable RLS
    ALTER TABLE processed_content ENABLE ROW LEVEL SECURITY;
    
    -- Create policies
    CREATE POLICY "Allow anonymous read processed_content" ON processed_content
        FOR SELECT USING (true);
    
    CREATE POLICY "Allow service role all operations on processed_content" ON processed_content
        FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
    
    -- Add comments
    COMMENT ON TABLE processed_content IS 'Stores generated newsletter content and metadata';
    COMMENT ON COLUMN processed_content.articles_count IS 'Number of articles processed in this newsletter';
    COMMENT ON COLUMN processed_content.multi_source_topics IS 'Number of multi-source topics identified';
    
    RAISE NOTICE 'Created processed_content table';
END IF;

-- Create processing_logs table if it doesn't exist
IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'processing_logs') THEN
    CREATE TABLE processing_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        processing_date DATE NOT NULL,
        edition VARCHAR NOT NULL,
        status VARCHAR NOT NULL, -- 'success', 'partial', 'failed'
        articles_processed INTEGER DEFAULT 0,
        articles_failed INTEGER DEFAULT 0,
        llm_calls INTEGER DEFAULT 0,
        total_tokens INTEGER DEFAULT 0,
        processing_time_seconds FLOAT,
        data JSONB DEFAULT '{}', -- Detailed processing information
        error_details TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    
    -- Create indexes
    CREATE INDEX idx_processing_logs_date ON processing_logs(processing_date);
    CREATE INDEX idx_processing_logs_status ON processing_logs(status);
    CREATE INDEX idx_processing_logs_created_at ON processing_logs(created_at);
    
    -- Enable RLS
    ALTER TABLE processing_logs ENABLE ROW LEVEL SECURITY;
    
    -- Create policies
    CREATE POLICY "Allow anonymous read processing_logs" ON processing_logs
        FOR SELECT USING (true);
    
    CREATE POLICY "Allow service role all operations on processing_logs" ON processing_logs
        FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
    
    -- Add comments
    COMMENT ON TABLE processing_logs IS 'Logs processing execution details and performance metrics';
    COMMENT ON COLUMN processing_logs.data IS 'Detailed processing information in JSON format';
    
    RAISE NOTICE 'Created processing_logs table';
END IF;

-- If processed_content table exists but missing columns, add them
IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'processed_content') THEN
    -- Add articles_count column if missing
    IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'processed_content' AND column_name = 'articles_count') THEN
        ALTER TABLE processed_content ADD COLUMN articles_count INTEGER NOT NULL DEFAULT 0;
        COMMENT ON COLUMN processed_content.articles_count IS 'Number of articles processed in this newsletter';
        RAISE NOTICE 'Added articles_count column to processed_content table';
    END IF;
    
    -- Add multi_source_topics column if missing
    IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'processed_content' AND column_name = 'multi_source_topics') THEN
        ALTER TABLE processed_content ADD COLUMN multi_source_topics INTEGER DEFAULT 0;
        COMMENT ON COLUMN processed_content.multi_source_topics IS 'Number of multi-source topics identified';
        RAISE NOTICE 'Added multi_source_topics column to processed_content table';
    END IF;
    
    -- Add metadata column if missing
    IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'processed_content' AND column_name = 'metadata') THEN
        ALTER TABLE processed_content ADD COLUMN metadata JSONB DEFAULT '{}';
        RAISE NOTICE 'Added metadata column to processed_content table';
    END IF;
END IF;

-- If processing_logs table exists but missing columns, add them
IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'processing_logs') THEN
    -- Add data column if missing
    IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'processing_logs' AND column_name = 'data') THEN
        ALTER TABLE processing_logs ADD COLUMN data JSONB DEFAULT '{}';
        COMMENT ON COLUMN processing_logs.data IS 'Detailed processing information in JSON format';
        RAISE NOTICE 'Added data column to processing_logs table';
    END IF;
    
    -- Add processing_time_seconds column if missing
    IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'processing_logs' AND column_name = 'processing_time_seconds') THEN
        ALTER TABLE processing_logs ADD COLUMN processing_time_seconds FLOAT;
        RAISE NOTICE 'Added processing_time_seconds column to processing_logs table';
    END IF;
END IF;

END $$;

-- Create helpful views for monitoring and debugging
CREATE OR REPLACE VIEW newsletter_processing_summary AS
SELECT 
    pc.processing_date,
    pc.edition,
    pc.title,
    pc.articles_count,
    pc.multi_source_topics,
    pl.status,
    pl.articles_processed,
    pl.articles_failed,
    pl.processing_time_seconds,
    pc.created_at
FROM processed_content pc
LEFT JOIN processing_logs pl ON pc.processing_date = pl.processing_date AND pc.edition = pl.edition
ORDER BY pc.processing_date DESC, pc.created_at DESC;

-- Create view for quality monitoring
CREATE OR REPLACE VIEW processing_quality_metrics AS
SELECT 
    processing_date,
    edition,
    status,
    CASE 
        WHEN articles_processed > 0 THEN (articles_processed::float / (articles_processed + articles_failed)) * 100
        ELSE 0 
    END as success_rate,
    articles_processed,
    articles_failed,
    processing_time_seconds,
    llm_calls,
    total_tokens,
    created_at
FROM processing_logs
ORDER BY processing_date DESC, created_at DESC;

-- Grant permissions on views
GRANT SELECT ON newsletter_processing_summary TO anon, authenticated;
GRANT SELECT ON processing_quality_metrics TO anon, authenticated;

-- Create function to clean up old logs (optional, for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_processing_logs(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM processing_logs 
    WHERE created_at < NOW() - (days_to_keep || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Cleaned up % old processing log records', deleted_count;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission on cleanup function
GRANT EXECUTE ON FUNCTION cleanup_old_processing_logs TO service_role;

RAISE NOTICE 'Phase 4 database migration completed successfully';