# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the AI News App (codename "Hokusai") - a newsletter automation system that:
- Collects AI news from RSS feeds and YouTube channels daily
- Uses multi-LLM summarization (Gemini → Claude → GPT-4o fallback strategy)
- Generates Japanese AI newsletters in Markdown format
- Runs automated daily at 09:00 JST via GitHub Actions
- Implements advanced deduplication using embeddings and context analysis

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright for OGP image generation (Phase 2+)
playwright install chromium

# Run main newsletter generation
python3 main.py --max-items 30 --edition daily

# Run tests (when implemented)
pytest tests/ -v

# Run with specific output directory
python main.py --max-items 30 --edition daily --output-dir drafts/

# Check logs
tail -f logs/newsletter_$(date +%Y-%m-%d).json

# python
puthon3
```

## Architecture & Key Technologies

- **Workflow Engine**: LangGraph for state management and node-based processing
- **LLM Integration**: Multi-provider fallback (Gemini 2.5 Pro → Claude 3.7 Sonnet → GPT-4o-mini)
- **Vector Database**: FAISS for local similarity search, eventual migration to Supabase pgvector
- **Data Validation**: Pydantic models for structured LLM outputs
- **Database**: Supabase for content storage and processing logs
- **Automation**: GitHub Actions with daily cron schedule

## Implementation Phases

Based on the PRD, development follows 5 phases:

1. **Phase 1**: Basic RSS/YouTube collection and LLM summarization
2. **Phase 2**: Context reflection system with embedding-based similarity search
3. **Phase 3**: Quality assurance, topic clustering, and structured outputs
4. **Phase 4**: Quaily platform integration and full automation
5. **Phase 5**: Advanced features (OGP images, optimization)

## Key File Structure

```
src/
├── main.py                          # Entry point
├── workflow/
│   └── newsletter_workflow.py       # LangGraph workflow definition
├── models/
│   └── schemas.py                   # Pydantic models
├── llm/
│   └── llm_router.py               # Multi-LLM fallback logic
├── deduplication/
│   └── duplicate_checker.py        # Hybrid similarity checking
├── utils/
│   └── error_handler.py            # Retry and fallback strategies
├── prompts/
│   ├── summary.yaml                # LLM prompts
│   └── context_analysis.yaml       # Context judging prompts
└── templates/
    └── daily_newsletter.jinja2     # Markdown template

data/
├── faiss/
│   └── index.bin                   # FAISS similarity index
└── logs/
    └── newsletter_YYYY-MM-DD.json  # Processing logs

drafts/
└── YYYY-MM-DD_newsletter.md        # Generated newsletters

tests/
└── test_*.py                       # test related files
```

## Database Schema (Supabase)

Key tables:
- `processed_content`: Stores generated newsletter content
- `processing_logs`: Execution logs and metrics
- `contextual_articles`: Embedding vectors and article relationships
- `article_relationships`: Links between related/sequel articles
- `content_sources`: RSS/YouTube source configuration

## Development Guidelines

### LLM Usage Patterns
- Always implement the 3-tier fallback: Gemini → Claude → GPT-4o-mini
- Use structured outputs with Pydantic validation
- Implement retry logic with exponential backoff
- Track costs and token usage in processing logs

### Quality Controls
- Generate 3-4 bullet points per article summary
- Enforce Japanese output with forbidden phrase detection
- Implement duplicate detection with >0.85 similarity threshold
- Add 🆙 emoji for sequel/update articles

### Error Handling
- Never fail completely - always provide fallback summaries
- Log all failures with LangSmith run IDs for debugging
- Implement circuit breaker patterns for external APIs

### Testing Strategy
- Use pytest for unit tests
- Test LLM output validation with regex patterns
- Verify newsletter format compliance
- Mock external API calls for reliable testing

## Environment Variables

Required secrets for GitHub Actions:
- `OPENAI_API_KEY`: For embeddings and GPT-4o fallback
- `GEMINI_API_KEY`: Primary LLM provider
- `CLAUDE_API_KEY`: Secondary LLM fallback
- `SUPABASE_URL`: Database connection
- `SUPABASE_KEY`: Database authentication
- `LANGSMITH_API_KEY`: LLM tracing and monitoring


## Performance Targets

- Daily execution time: <5 minutes for 30 articles
- LLM API cost: <$1/day
- Success rate: >95%
- Duplicate detection: <5% false negatives per week

## Current Status

This is an early-stage project with comprehensive PRD documentation. The actual implementation should follow the phased approach outlined in the PRD, starting with Phase 1 basic functionality.

## Gemini CLI Integration

### 目的
ユーザーが **「Geminiと相談しながら進めて」** （または同義語）と指示した場合、Claude は以降のタスクを **Gemini CLI** と協調しながら進める。
Gemini から得た回答はそのまま提示し、Claude 自身の解説・統合も付け加えることで、両エージェントの知見を融合する。

---

### トリガー
- 正規表現: `/Gemini.*相談しながら/`
- 例:
- 「Geminiと相談しながら進めて」
- 「この件、Geminiと話しつつやりましょう」

---

### 基本フロー
1. **PROMPT 生成**
Claude はユーザーの要件を 1 つのテキストにまとめ、環境変数 `$PROMPT` に格納する。

2. **Gemini CLI 呼び出し**
```bash
gemini <<EOF
$PROMPT
EOF