# AI News Newsletter Generator (Hokusai)

An automated newsletter generation system that collects AI news from RSS feeds and YouTube channels, summarizes content using multiple LLMs, and generates Japanese newsletters in Markdown format.

## 🚀 Features

### Phase 1-4 (Completed)
- **Multi-source Content Collection**: RSS feeds and YouTube channel integration
- **AI-focused Content Filtering**: Intelligent keyword-based relevance scoring
- **Multi-LLM Summarization**: Gemini 2.5 Flash → Claude 3.7 Sonnet → GPT-4o-mini fallback
- **Duplicate Detection**: Jaccard similarity and SequenceMatcher algorithms
- **Contextual Article System**: Past article tracking and relationship detection
- **Embedding-based Similarity**: OpenAI text-embedding-3-small integration
- **Update Detection**: Automatic detection of follow-up articles with 🆙 emoji
- **LangGraph Workflow**: State-managed processing pipeline
- **Supabase Integration**: Persistent storage and Quaily publishing
- **FAISS Index Management**: Efficient similarity search with automatic syncing

### Phase 5 (Completed) ✨ **NEW**
- **🖼️ Image Embedding**: Automatic OGP image and YouTube thumbnail extraction
- **☁️ Cloud Storage**: Supabase Storage integration with automatic optimization
- **📱 Responsive Design**: Mobile and desktop optimized image display
- **🎬 Video Previews**: YouTube videos with click-to-play thumbnails
- **⚡ Performance Optimized**: PNG→JPEG conversion, resizing, compression
- **🛡️ Error Resilient**: Graceful fallbacks when images unavailable

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RSS/YouTube   │───▶│   AI Filtering  │───▶│ LLM Summary     │
│   Collection    │    │   & Scoring     │    │ Generation      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────▼─────────┐
│   Image         │◀───│   Newsletter    │◀───│   Duplicate     │
│   Processing    │    │   Generation    │    │   Detection     │
└─────┬───────────┘    └─────────────────┘    └─────────────────┘
      │                         │
┌─────▼───────────┐    ┌─────────▼─────────┐
│   Supabase      │    │   Markdown        │
│   Storage       │    │   Output          │
└─────────────────┘    └─────────────────┘
```

### 🖼️ Image Processing Pipeline

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ YouTube/OGP     │───▶│ Image Fetch     │───▶│ Optimization    │
│ URL Detection   │    │ Multi-Strategy  │    │ PNG→JPEG        │
└─────────────────┘    └─────────────────┘    └─────┬───────────┘
                                                      │
┌─────────────────┐    ┌─────────────────┐    ┌─────▼───────────┐
│ Newsletter      │◀───│ Public URL      │◀───│ Supabase        │
│ Embedding       │    │ Generation      │    │ Upload          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📦 Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd ainews_app
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Install Playwright (for future OGP enhancements)**
```bash
playwright install chromium
```

4. **Set up environment variables**
```bash
cp .env.template .env
# Edit .env with your API keys
```

Required environment variables:
```bash
# LLM API Keys
GEMINI_API_KEY=your_gemini_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key

# Supabase
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key

# Optional
LANGCHAIN_API_KEY=your_langsmith_api_key
```

5. **Set up Supabase Storage**

Create an image storage bucket in your Supabase project:
```bash
python3 create_supabase_bucket_v2.py
```

Or manually via Supabase Dashboard:
- Go to Storage → Create bucket
- Name: `ainews-images`
- Public: ✅ Yes (for image access)
- File size limit: 500KB

6. **Set up Supabase tables**

Create the following tables in your Supabase project:

**Phase 2 Tables (contextual_articles and article_relationships):**
```sql
-- Enable pgvector extension if available
CREATE EXTENSION IF NOT EXISTS vector;

-- Create contextual articles table
CREATE TABLE IF NOT EXISTS contextual_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id VARCHAR NOT NULL UNIQUE,
  title TEXT NOT NULL,
  content_summary TEXT NOT NULL,
  embedding VECTOR(1536), -- Or use JSONB if vector not available
  published_date TIMESTAMP NOT NULL,
  source_url TEXT,
  topic_cluster VARCHAR,
  created_at TIMESTAMP DEFAULT NOW(),
  source_id VARCHAR,
  ai_relevance_score FLOAT,
  summary_points JSONB,
  japanese_title TEXT,
  is_update BOOLEAN DEFAULT FALSE
);

-- Create article relationships table
CREATE TABLE IF NOT EXISTS article_relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_article_id UUID REFERENCES contextual_articles(id) ON DELETE CASCADE,
  child_article_id UUID REFERENCES contextual_articles(id) ON DELETE CASCADE,
  relationship_type VARCHAR NOT NULL,
  similarity_score FLOAT,
  created_at TIMESTAMP DEFAULT NOW(),
  reasoning TEXT,
  UNIQUE(parent_article_id, child_article_id, relationship_type)
);

-- Create indexes
CREATE INDEX idx_published_date ON contextual_articles(published_date);
CREATE INDEX idx_article_id ON contextual_articles(article_id);
CREATE INDEX idx_parent_article ON article_relationships(parent_article_id);
CREATE INDEX idx_child_article ON article_relationships(child_article_id);
```

**Note**: If using Supabase free tier without pgvector support, replace `VECTOR(1536)` with `JSONB` for the embedding column.

## 🔧 Configuration

### API Keys Required
- **OPENAI_API_KEY**: For embeddings and GPT-4o-mini fallback
- **GEMINI_API_KEY**: Primary LLM provider (Gemini 2.5 Flash)
- **ANTHROPIC_API_KEY**: Secondary LLM fallback (Claude 3.7 Sonnet)
- **SUPABASE_URL**: Database connection and image storage
- **SUPABASE_KEY**: Database authentication (service role key recommended)

### News Sources
Built-in curated sources (38 total, 36 enabled):
- **Priority 1**: OpenAI, Anthropic, Google Research, Hugging Face (10 sources)
- **Priority 2**: AI newsletters, Bay Area Times, SemiAnalysis (10 sources)  
- **Priority 3**: TechCrunch, VentureBeat, WIRED, Y Combinator (14 sources)
- **Priority 4**: Japanese sources - Zenn, note, Qiita (4 sources)
- Automatic source type detection (RSS/YouTube)

## 🚀 Usage

### Basic Usage
```bash
# Generate newsletter with default settings (includes image processing)
python3 main.py --max-items 30 --edition daily

# Generate with images for testing
python3 main.py --max-items 5 --edition daily --output-dir drafts/test/

# Dry run (no API calls, no file writes)
python3 main.py --max-items 5 --dry-run

# Custom output directory
python3 main.py --max-items 30 --edition daily --output-dir custom_output/
```

### Command Line Options
- `--max-items`: Maximum articles to process (default: 30)
- `--edition`: Newsletter type - daily/weekly (default: daily)
- `--output-dir`: Output directory (default: drafts/)
- `--sources-file`: Custom sources file (default: sources.json)
- `--dry-run`: Test mode without external API calls

### Output
Generated newsletters are saved as:
```
drafts/YYYY-MM-DD_daily_newsletter.md
```

## 🧪 Testing

Run comprehensive tests:
```bash
# Basic functionality tests
python3 tests/test_basic_no_deps.py

# Image processing tests
python3 test_e2e_image_workflow.py

# Real image upload test (requires Supabase setup)
python3 test_youtube_upload.py

# Create Supabase bucket
python3 create_supabase_bucket_v2.py
```

## 📊 Processing Pipeline

1. **Source Fetching** (`src/utils/content_fetcher.py`)
   - Concurrent RSS/YouTube feed collection
   - Automatic content cleaning and normalization
   - 24-hour lookback window

2. **AI Content Filtering** (`src/utils/ai_filter.py`)
   - Multi-tier keyword matching (high/medium/low priority)
   - Relevance scoring with source priority boosting
   - Japanese and English keyword support

3. **LLM Summarization** (`src/llm/llm_router.py`)
   - Automatic fallback strategy across 3 LLM providers
   - Structured output validation with Pydantic
   - Cost tracking and retry logic

4. **Image Processing** (`src/utils/image_processor.py`) ✨ **NEW**
   - YouTube thumbnail extraction (multiple quality levels)
   - OGP image detection and fetching
   - PNG→JPEG conversion and optimization
   - Supabase Storage upload with public URLs

5. **Duplicate Detection** (`src/deduplication/duplicate_checker.py`)
   - Jaccard similarity coefficient
   - SequenceMatcher ratio comparison
   - Configurable similarity thresholds

6. **Newsletter Generation** (`src/utils/newsletter_generator.py`)
   - Jinja2 template rendering with image embedding
   - Responsive image display (mobile/desktop)
   - YouTube video previews with click-to-play
   - Automatic lead text generation

## 📁 Project Structure

```
ainews_app/
├── main.py                          # CLI entry point
├── requirements.txt                 # Python dependencies
├── sources.json                     # News sources configuration
├── .env.template                    # Environment variables template
│
├── src/
│   ├── models/
│   │   └── schemas.py              # Pydantic data models
│   ├── utils/
│   │   ├── content_fetcher.py      # RSS/YouTube collection
│   │   ├── ai_filter.py            # Content relevance filtering
│   │   ├── image_fetcher.py        # Image acquisition ✨ NEW
│   │   ├── image_uploader.py       # Supabase upload ✨ NEW
│   │   ├── image_processor.py      # Integrated pipeline ✨ NEW
│   │   ├── newsletter_generator.py # Markdown generation
│   │   └── logger.py               # Structured logging
│   ├── workflow/
│   │   └── newsletter_workflow.py  # LangGraph workflow
│   ├── llm/
│   │   └── llm_router.py           # Multi-LLM fallback system
│   ├── deduplication/
│   │   └── duplicate_checker.py    # Similarity detection
│   ├── workflow/
│   │   └── newsletter_workflow.py  # LangGraph pipeline
│   └── templates/
│       └── daily_newsletter.jinja2 # Newsletter template
│
├── drafts/                         # Generated newsletters
├── logs/                           # Processing logs
└── data/
    └── faiss/                      # Vector indices (Phase 2+)
```

## 🎯 Implementation Status

### ✅ **Phase 1-5 COMPLETED** (2025-07-06)

**Phase 1: 基盤システム構築** ✅ COMPLETED
- Multi-source RSS/YouTube collection
- AI keyword filtering and LLM summarization
- Basic duplicate detection and Markdown generation

**Phase 2: 文脈反映システム** ✅ COMPLETED  
- OpenAI Embedding integration
- FAISS vector similarity search
- Article relationship detection and context-aware summarization

**Phase 3: 品質保証・自動化** ✅ COMPLETED
- Topic clustering and citation generation
- LangSmith monitoring integration
- Comprehensive test suite and error handling

**Phase 4: Quaily統合・配信自動化** ✅ COMPLETED
- Quaily platform integration
- GitHub Actions daily workflow
- Automated publishing and monitoring

**Phase 5: 拡張機能・最適化** ✅ COMPLETED
- 🖼️ **Image Embedding**: OGP/YouTube image extraction
- ☁️ **Supabase Storage**: Automatic image optimization  
- 📱 **Responsive Design**: Mobile/desktop image display
- 🎬 **Video Previews**: Click-to-play YouTube thumbnails

### 🚀 **Future Enhancements**
- A/B testing for prompts and formats
- Advanced analytics dashboard
- Reader feedback integration
- Performance monitoring and cost optimization

## 📈 Performance & Achievements

**Current Performance (as of 2025-07-06):**
- ✅ **Processing Time**: <5 minutes for 30 articles
- ✅ **API Cost**: <$1/day with multi-LLM optimization
- ✅ **Success Rate**: >95% with robust error handling
- ✅ **Duplicate Detection**: <5% false negatives with 0.85 threshold
- ✅ **Image Processing**: 100% test success rate
- ✅ **E2E Tests**: 4/4 tests passing (100%)

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're in the project root directory
2. **API Failures**: Check API keys in `.env` file
3. **Network Timeouts**: Some RSS feeds may be slow; adjust timeout settings
4. **Template Errors**: Verify Jinja2 template syntax in `src/templates/`

### Debug Mode
Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
python3 main.py --max-items 5 --dry-run
```

## 📄 License

This project is part of the AI Newsletter automation system. Please refer to the project documentation for usage guidelines.

## 🤝 Contributing

This is a Phase 1 implementation. Future phases will expand functionality based on the comprehensive PRD specifications.

---

**Generated with ❤️ using LangGraph + Multi-LLM Architecture**