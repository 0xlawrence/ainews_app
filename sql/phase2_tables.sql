-- Phase 2: Contextual Articles Tables
-- PRDに記載されているテーブル定義

-- 記事のEmbeddingと文脈情報を保存
CREATE TABLE IF NOT EXISTS contextual_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id VARCHAR NOT NULL UNIQUE,
    title TEXT NOT NULL,
    content_summary TEXT NOT NULL,
  embedding VECTOR(1536), -- OpenAI text-embedding-3-small
    published_date TIMESTAMP NOT NULL,
    source_url TEXT,
    topic_cluster VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
  
  -- 追加のメタデータ
  source_id VARCHAR,
  ai_relevance_score FLOAT,
  summary_points JSONB, -- 要約の箇条書きを保存
  japanese_title TEXT,
  is_update BOOLEAN DEFAULT FALSE
);

-- インデックス
CREATE INDEX idx_published_date ON contextual_articles(published_date);
CREATE INDEX idx_article_id ON contextual_articles(article_id);

-- 記事間の関係性を記録
CREATE TABLE IF NOT EXISTS article_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_article_id UUID REFERENCES contextual_articles(id) ON DELETE CASCADE,
    child_article_id UUID REFERENCES contextual_articles(id) ON DELETE CASCADE,
  relationship_type VARCHAR NOT NULL, -- 'sequel', 'related', 'update'
  similarity_score FLOAT,
  created_at TIMESTAMP DEFAULT NOW(),
  
  -- 関係性の詳細
  reasoning TEXT, -- LLMによる判定理由
  
  -- 複合ユニーク制約（同じ関係は1つだけ）
  UNIQUE(parent_article_id, child_article_id, relationship_type)
);

-- インデックス
CREATE INDEX idx_parent_article ON article_relationships(parent_article_id);
CREATE INDEX idx_child_article ON article_relationships(child_article_id);
CREATE INDEX idx_relationship_type ON article_relationships(relationship_type);

-- pgvectorの拡張が必要な場合
-- CREATE EXTENSION IF NOT EXISTS vector;

-- RLSポリシー（読み取り専用）
ALTER TABLE contextual_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_relationships ENABLE ROW LEVEL SECURITY;

-- anon roleは読み取りのみ
CREATE POLICY "Allow anonymous read contextual_articles" ON contextual_articles
  FOR SELECT USING (true);

CREATE POLICY "Allow anonymous read article_relationships" ON article_relationships
  FOR SELECT USING (true);

-- service roleは全操作可能
CREATE POLICY "Allow service role all operations on contextual_articles" ON contextual_articles
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Allow service role all operations on article_relationships" ON article_relationships
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- 生成されたニュースレターコンテンツを保存
CREATE TABLE IF NOT EXISTS processed_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    processing_date DATE NOT NULL,
    edition VARCHAR NOT NULL, -- 'daily', 'weekly', etc.
    content_type VARCHAR NOT NULL, -- 'newsletter', 'summary', etc.
    title TEXT NOT NULL,
    lead_paragraph TEXT,
    articles_count INTEGER NOT NULL,
    multi_source_topics INTEGER DEFAULT 0,
    content_md TEXT NOT NULL, -- Generated markdown content
    metadata JSONB, -- Additional metadata (topics, sources, etc.)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 複合ユニーク制約
    UNIQUE(processing_date, edition, content_type)
);

-- 処理ログを保存
CREATE TABLE IF NOT EXISTS processing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    processing_date DATE NOT NULL,
    edition VARCHAR NOT NULL,
    status VARCHAR NOT NULL, -- 'success', 'partial', 'failed'
    articles_processed INTEGER DEFAULT 0,
    articles_failed INTEGER DEFAULT 0,
    llm_calls INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    processing_time_seconds FLOAT,
    data JSONB, -- Detailed processing information
    error_details TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- インデックス
    INDEX(processing_date),
    INDEX(status),
    INDEX(created_at)
);

-- インデックス
CREATE INDEX idx_processed_content_date ON processed_content(processing_date);
CREATE INDEX idx_processed_content_edition ON processed_content(edition);
CREATE INDEX idx_processing_logs_date ON processing_logs(processing_date);
CREATE INDEX idx_processing_logs_status ON processing_logs(status);

-- RLSポリシー
ALTER TABLE processed_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_logs ENABLE ROW LEVEL SECURITY;

-- anon roleは読み取りのみ
CREATE POLICY "Allow anonymous read processed_content" ON processed_content
  FOR SELECT USING (true);

CREATE POLICY "Allow anonymous read processing_logs" ON processing_logs
  FOR SELECT USING (true);

-- service roleは全操作可能
CREATE POLICY "Allow service role all operations on processed_content" ON processed_content
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Allow service role all operations on processing_logs" ON processing_logs
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Comments for documentation
COMMENT ON TABLE contextual_articles IS 'Stores articles with embeddings for similarity search and context analysis';
COMMENT ON TABLE article_relationships IS 'Tracks relationships between articles (sequels, updates, related content)';
COMMENT ON TABLE processed_content IS 'Stores generated newsletter content and metadata';
COMMENT ON TABLE processing_logs IS 'Logs processing execution details and performance metrics';

COMMENT ON COLUMN contextual_articles.embedding IS 'OpenAI text-embedding-3-small vector (1536 dimensions)';
COMMENT ON COLUMN contextual_articles.topic_cluster IS 'Topic cluster identifier for grouping related articles';
COMMENT ON COLUMN article_relationships.relationship_type IS 'Type of relationship: sequel, related, update';
COMMENT ON COLUMN article_relationships.reasoning IS 'Reasoning for the relationship determination';
COMMENT ON COLUMN processed_content.articles_count IS 'Number of articles processed in this newsletter';
COMMENT ON COLUMN processed_content.multi_source_topics IS 'Number of multi-source topics identified';
COMMENT ON COLUMN processing_logs.data IS 'Detailed processing information in JSON format';

-- Sample data views for development
CREATE OR REPLACE VIEW recent_contextual_articles AS
SELECT 
    article_id,
    title,
    topic_cluster,
    ai_relevance_score,
    published_date,
    created_at
FROM contextual_articles
WHERE published_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY published_date DESC;

CREATE OR REPLACE VIEW article_relationship_summary AS
SELECT 
    relationship_type,
    COUNT(*) as relationship_count,
    AVG(similarity_score) as avg_similarity,
    MIN(similarity_score) as min_similarity,
    MAX(similarity_score) as max_similarity
FROM article_relationships
GROUP BY relationship_type
ORDER BY relationship_count DESC;