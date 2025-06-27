# AI News Newsletter Generator (Hokusai)

An automated newsletter generation system that collects AI news from RSS feeds and YouTube channels, summarizes content using multiple LLMs, and generates Japanese newsletters in Markdown format.

## 🚀 Features

### Phase 1 (Completed)
- **Multi-source Content Collection**: RSS feeds and YouTube channel integration
- **AI-focused Content Filtering**: Intelligent keyword-based relevance scoring
- **Multi-LLM Summarization**: Gemini 2.5 Pro → Claude 3.7 Sonnet → GPT-4o-mini fallback
- **Duplicate Detection**: Jaccard similarity and SequenceMatcher algorithms
- **Markdown Newsletter Generation**: Clean, structured Japanese newsletters
- **LangGraph Workflow**: State-managed processing pipeline
- **Comprehensive Logging**: Structured JSON logging with processing metrics

### Phase 2 (Completed)
- **Contextual Article System**: Past article tracking and relationship detection
- **Embedding-based Similarity**: OpenAI text-embedding-3-small integration
- **Update Detection**: Automatic detection of follow-up articles with 🆙 emoji
- **Supabase Integration**: Persistent storage of articles and relationships
- **FAISS Index Management**: Efficient similarity search with automatic syncing

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RSS/YouTube   │───▶│   AI Filtering  │───▶│ LLM Summary     │
│   Collection    │    │   & Scoring     │    │ Generation      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────▼─────────┐
│   Markdown      │◀───│   Newsletter    │◀───│   Duplicate     │
│   Output        │    │   Generation    │    │   Detection     │
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

3. **Set up environment variables**
```bash
cp .env.template .env
# Edit .env with your API keys
```

4. **Set up Supabase tables**

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

5. **Install Playwright (for future phases)**
```bash
playwright install chromium
```

## 🔧 Configuration

### API Keys Required
- **OPENAI_API_KEY**: For embeddings and GPT-4o-mini fallback
- **GEMINI_API_KEY**: Primary LLM provider (Gemini 2.5 Pro)
- **CLAUDE_API_KEY**: Secondary LLM fallback (Claude 3.7 Sonnet)
- **SUPABASE_URL**: Database connection (optional for Phase 1)
- **SUPABASE_KEY**: Database authentication (optional for Phase 1)

### News Sources
Configure RSS feeds and YouTube channels in `sources.json`:
- 19 enabled sources including OpenAI, Anthropic, Google Research
- Mix of official channels and curated AI news outlets
- Automatic source type detection (RSS/YouTube)

## 🚀 Usage

### Basic Usage
```bash
# Generate newsletter with default settings
python3 main.py --max-items 30 --edition daily

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

Run basic functionality tests:
```bash
# Test without dependencies
python3 test_basic_no_deps.py

# Test with dependencies (requires pip install)
python3 test_basic.py
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

4. **Duplicate Detection** (`src/deduplication/duplicate_checker.py`)
   - Jaccard similarity coefficient
   - SequenceMatcher ratio comparison
   - Configurable similarity thresholds

5. **Newsletter Generation** (`src/utils/newsletter_generator.py`)
   - Jinja2 template rendering
   - Automatic lead text generation
   - Processing statistics inclusion

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
│   │   ├── newsletter_generator.py # Markdown generation
│   │   └── logger.py               # Structured logging
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

## 🔮 Roadmap

### Phase 2: Context Reflection System ✅ COMPLETED
- ✅ OpenAI Embedding integration
- ✅ FAISS vector similarity search
- ✅ Article relationship detection
- ✅ Context-aware summarization
- ✅ Supabase persistent storage
- ✅ Automatic past article loading

### Phase 3: Quality Assurance
- Advanced topic clustering
- Citation system with source links
- LangSmith monitoring integration
- Comprehensive test suite

### Phase 4: Production Automation
- Quaily platform integration
- GitHub Actions daily workflow
- Slack notifications
- Error monitoring and alerting

### Phase 5: Advanced Features
- OGP image generation
- A/B testing for prompts
- Performance optimization
- Reader feedback integration

## 📈 Performance Targets

- **Processing Time**: <5 minutes for 30 articles
- **API Cost**: <$1/day
- **Success Rate**: >95%
- **Duplicate Detection**: <5% false negatives/week

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