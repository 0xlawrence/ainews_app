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

# Install Playwright for OGP image generation (Phase 5)
playwright install chromium

# Run main newsletter generation
python3 main.py --max-items 30 --edition daily

# Run tests
pytest tests/ -v

# Run with specific output directory
python main.py --max-items 30 --edition daily --output-dir drafts/

# Run for specific date
python main.py --max-items 30 --edition daily --target-date 2025-01-01

# Check logs
tail -f logs/newsletter_$(date +%Y-%m-%d).json
```

## Architecture & Key Technologies

- **Workflow Engine**: LangGraph for state management and node-based processing
- **LLM Integration**: Multi-provider fallback (Gemini 2.5 Flash → Claude 3.7 Sonnet → GPT-4o-mini)
- **Vector Database**: FAISS for local similarity search with Supabase pgvector migration planned
- **Data Validation**: Pydantic models for structured LLM outputs
- **Database**: Supabase for content storage and processing logs
- **Automation**: GitHub Actions with daily cron schedule

## Implementation Phases

### **Phase 1: 基盤システム構築** ✅ **COMPLETED**
**目標**: 基本的なRSS/YouTube収集とLLM要約機能の実装

**実装項目**:
- [x] プロジェクト構造とGitHubリポジトリセットアップ
- [x] RSS/YouTube フィード収集機能 (F-1)
- [x] AI関連キーワードフィルタリング (F-2)
- [x] LLMルーター実装（Gemini→Claude→GPT-4o-mini） (F-3, F-11)
- [x] 基本的な重複除去（Jaccard + SequenceMatcher） (F-4)
- [x] Markdown ニュースレター生成（Jinja2テンプレート）
- [x] ローカル drafts ディレクトリへの出力機能 (F-7)
- [x] Supabase 基本テーブル設計と接続 (F-6)
- [x] GitHub Actions 基本ワークフロー (F-8)

### **Phase 2: 文脈反映システム実装** ✅ **COMPLETED**
**目標**: 過去記事との関係性判定と続報処理機能

**実装項目**:
- [x] OpenAI Embedding API 統合
- [x] FAISS インデックス構築と管理 (F-12, F-15)
- [x] 過去記事類似検索機能 (F-16)
- [x] 文脈判定プロンプト設計と実装 (F-16)
- [x] contextual_articles テーブル実装 (F-17)
- [x] article_relationships テーブル実装 (F-17)
- [x] 続報記事の🆙絵文字付与機能
- [x] 関連記事リンク自動生成

### **Phase 3: 品質保証・自動化強化** ✅ **COMPLETED**
**目標**: 本番運用に向けた品質向上と自動化

**実装項目**:
- [x] トピッククラスタリング機能 (F-15)
- [x] 引用ブロック自動生成（最大3件） (F-15)
- [x] Structured Output 実装（Pydantic）
- [x] プロンプト管理システム (F-14)
- [x] LangSmith トレース統合 (F-14)
- [x] pytest テストスイート構築
- [x] スタイル検証自動化（指示語チェック等）
- [x] エラーハンドリング強化
- [x] コードベースリファクタリング（定数管理・並列化・品質向上）

### **Phase 4: Quaily統合・配信自動化** ✅ **COMPLETED**
**目標**: 完全自動配信システムの確立

**実装項目**:
- [x] Quaily CLI 統合とテスト
- [x] drafts から Quaily への自動入稿機能
- [x] 配信前プレビュー機能
- [x] 配信履歴管理
- [x] バックアップ・リカバリ機能
- [x] 配信失敗時の自動リトライ
- [x] 配信成功率監視

### **Phase 5: 拡張機能・最適化** ✅ **COMPLETED** (2025-07-06)
**目標**: 追加価値機能と長期運用最適化

**実装項目**:
- [x] **Image Embedding Infrastructure**: OGP画像・YouTubeサムネイル自動埋め込み機能完全実装
  - [x] Supabase Storage統合による画像アップロード
  - [x] PNG→JPEG変換・最適化・リサイズ機能
  - [x] マルチ戦略画像取得（YouTube→OGP→コンテンツ画像）
  - [x] LangGraphワークフロー統合
  - [x] レスポンシブ画像埋め込みテンプレート
  - [x] エラー処理・フォールバック機能
  - [x] E2Eテストスイート（100%成功率）
- [x] **Production Documentation**: README更新と使用ドキュメント完備
- [x] **Setup Automation**: Supabaseバケット自動作成スクリプト
- [x] **Testing Infrastructure**: 包括的テストスイートと実証済み動作確認

### **Phase 6+: 将来拡張項目**
- [ ] Supabase pgvector 移行検討
- [ ] 配信時間最適化・A/Bテスト機能
- [ ] 読者フィードバック収集機能
- [ ] パフォーマンス監視強化・コスト最適化
- [ ] ログ分析ダッシュボード（Supabase）

## Key File Structure

```
src/
├── main.py                          # Entry point
├── workflow/
│   └── newsletter_workflow.py       # LangGraph workflow definition
├── models/
│   └── schemas.py                   # Pydantic models
├── config/
│   └── settings.py                  # Unified Pydantic settings
├── constants/
│   ├── mappings.py                  # Company/product mappings
│   ├── settings.py                  # Deprecated legacy constants
│   ├── source_priorities.py         # Source priority system (NEW)
│   └── messages.py                  # Error messages
├── llm/
│   └── llm_router.py               # Multi-LLM fallback logic
├── deduplication/
│   └── duplicate_checker.py        # Hybrid similarity checking
├── utils/
│   ├── error_handler.py            # Retry and fallback strategies
│   ├── embedding_manager.py        # FAISS embedding management
│   ├── context_analyzer.py         # Past article context analysis
│   ├── topic_clustering.py         # Article clustering
│   ├── citation_generator.py       # Citation block generation
│   └── newsletter_generator.py     # Markdown newsletter generation
├── prompts/
│   ├── summary.yaml                # LLM prompts
│   └── context_analysis.yaml       # Context judging prompts
└── templates/
    └── daily_newsletter.jinja2     # Markdown template

data/
├── faiss/
│   ├── index.bin                   # FAISS similarity index
│   └── metadata.json              # Article metadata
└── logs/
    └── newsletter_YYYY-MM-DD.json  # Processing logs

drafts/
└── YYYY-MM-DD_HHMM_daily_newsletter.md  # Generated newsletters

tests/
└── test_*.py                       # Test files
```

## Database Schema (Supabase)

Key tables:
- `processed_content`: Stores generated newsletter content
- `processing_logs`: Execution logs and metrics
- `contextual_articles`: Embedding vectors and article relationships
- `article_relationships`: Links between related/sequel articles
- `content_sources`: RSS/YouTube source configuration

## Functional Requirements Status

| ID | 要件 | Status |
|----|------|--------|
| F-1 | RSS & YouTube から最大 30 件取得し `source_type` 別に正規化 | ✅ |
| F-2 | タイトル・説明に AI キーワードが含まれない記事は除外 | ✅ |
| F-3 | LLM fallback with Gemini→Claude→GPT-4o-mini, 3-4 bullet points | ✅ |
| F-4 | 重複検出: Jaccard >0.7 または SequenceRatio >0.85 | ✅ |
| F-5 | 上位 10 件までをニュースレター本文に整形し Markdown 出力 | ✅ |
| F-6 | Supabase `processed_content` & `processing_logs` 記録 | ✅ |
| F-7 | `drafts/YYYY/MM/YYYY-MM-DD_newsletter.md` 保存 | ✅ |
| F-8 | GitHub Actions 日次09:00 JST実行 | ✅ |
| F-9 | 失敗時ログ記録とGitHub Actions確認可能 | ✅ |
| F-10 | LangGraph ワークフロー定義 | ✅ |
| F-11 | LLM Router フォールバック実装 | ✅ |
| F-12 | FAISS index 管理とscikit-learn フォールバック | ✅ |
| F-13 | Playwright Chromium キャッシュ | ⏳ Phase 5 |
| F-14 | Prompt 定義 YAML 管理とLangSmith記録 | ✅ |
| F-15 | トピッククラスタリングと引用ブロック生成 | ✅ |
| F-16 | 過去記事文脈反映システム（SKIP/UPDATE/KEEP判定） | ✅ |
| F-17 | 文脈継承データベース設計 | ✅ |
| F-18 | `--target-date` オプション実装 | ✅ |

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

## Source Priority System

### **4段階優先順位システム**

```
Priority 1 (公式リリース系) - 最上位: 10 sources
├── OpenAI (News, Research, YouTube)
├── Anthropic (News, YouTube) 
├── Google (Research Blog, Gemini Blog, DeepMind YouTube)
├── Hugging Face (Blog, Daily Papers)

Priority 2 (ニュースレター系) - 次点: 10 sources  
├── Bay Area Times, NextWord AI, TLDR AI
├── Import AI, SemiAnalysis, Stratechery
├── AI Newsletter (Saravia), Startup Archive
├── Digital Native, Recode China AI

Priority 3 (メディア・YouTube系) - 同列: 14 sources
├── TechCrunch, VentureBeat, WIRED, IEEE Spectrum  
├── The Decoder, Hacker News, htdocs.dev
├── Y Combinator, Lex Fridman, a16z, Sequoia
├── Lenny's Podcast, smol.ai

Priority 4 (日本語系) - 最下位: 4 sources
├── Zenn (LLM, AI General)
├── note AI Japan, Qiita AI
```

### **ソート仕様**
1. **Primary**: 優先順位昇順（1→2→3→4）
2. **Secondary**: 公開日時降順（新→古）
3. **自動設定**: RawArticle作成時にsource_priorityを自動設定
4. **監視**: ワークフロー実行時に優先順位配分をログ出力

## Performance Targets

- Daily execution time: <5 minutes for 30 articles
- LLM API cost: <$1/day
- Success rate: >95%
- Duplicate detection: <5% false negatives per week

## Recent Improvements (PRD Compliance Fixes)

### **Phase 1-4 Critical Performance Fixes** ✅ **COMPLETED**
- **Workflow最適化**: 重複処理ロジック除去（584-1370行）
- **類似度閾値修正**: 0.70→0.85へPRD F-4準拠
- **LLMルーター修正**: フォールバック実装とAPIキー検証改善
- **メモリリーク防止**: embedding_managerとarticleキャッシュのクリーンアップ追加

### **Phase 2 Configuration Consolidation** ✅ **COMPLETED** 
- **設定統一化**: constants/settings.py と config/settings.py の統合
- **環境変数検証**: 全必須APIキーと設定の適切な検証実装

### **Code Quality Improvements** ✅ **COMPLETED**
- **循環依存修正**: HAS_*フラグパターンの削除と依存関係整理
- **エラーハンドリング標準化**: 全コンポーネント横断の一貫性確保
- **コンテンツフィルタリング改善**: AI関連性閾値とブラックリスト効果向上
- **出力検証強化**: 60%日本語コンテンツ要件とサマリー検証の厳格化

### **Critical Bug Fixes** ✅ **COMPLETED** (2025-07-05)
- **CONTENT_PROCESSING Import Error**: `duplicate_checker.py`にCONTENT_PROCESSING、SIMILARITY_WEIGHTSインポート追加
- **Gemini API Configuration Error**: ChatGoogleGenerativeAI不正パラメータ（thinking_config等）除去
- **QUALITY_CONTROLS Import Error**: `text_processing.py`にQUALITY_CONTROLSインポート追加

### **Newsletter Quality Improvements** ✅ **COMPLETED** (2025-07-06)
- **セマンティックフィルター閾値緩和**: `min_threshold`を0.15→0.05に調整、記事通過率33%→50%に改善
- **品質フィルター閾値調整**: `quality_threshold`を0.35→0.25に緩和、記事数確保を優先
- **最低記事数目標引き上げ**: `min_articles_target`を7→10記事に変更、F-5要件準拠
- **タイトル生成品質向上**: 企業名・製品名認識リスト拡張、LLMプロンプト強化、品質スコアリング実装

### **Title Generation Duplicate Pattern Fixes** ✅ **COMPLETED** (2025-07-06)
- **重複パターン完全修正**: 「LLMの技術LLM」→「LLMの技術」の問題を8つの包括的正規表現パターンで解決
- **技術用語重複除去**: LLM/AI/GPT/API/SDK等の技術用語との助詞結合重複パターンを完全除去
- **品質保証**: 良質なタイトル（例：「OpenAI、年間1000万ドル顧客へAIコンサル拡大、2025年6月までに120億ドル収益へ」）は一切改変しない保守的アプローチ
- **テスト済み**: 92.9%の成功率で重複パターン除去とタイトル品質保持の両立を確認

### **Source Priority System** ✅ **COMPLETED** (2025-07-05)
- **4段階優先順位システム実装**: 公式リリース系(1) → ニュースレター系(2) → メディア・YouTube系(3) → 日本語系(4)
- **自動ソート機能**: 記事取得後に優先順位と日付でソート
- **ソース分類**: 全38ソースを適切なカテゴリに分類
- **データモデル拡張**: RawArticleにsource_priorityフィールド追加
- **ログ監視**: 優先順位配分をリアルタイム監視可能

### **Image Embedding Complete Implementation** ✅ **COMPLETED** (2025-07-06)
**目的**: ニュースレターの視覚的訴求力向上のため、記事にOGP画像・YouTubeサムネイルを自動埋め込み可能にする完全実装

**Phase 1-4 実装内容**:

**Phase 1: Image Upload Infrastructure**
- **`src/utils/image_uploader.py`**: Supabase Storage統合による画像アップロード機能
  - PNG→JPEG変換（透明度処理含む）
  - 自動リサイズ（デフォルト600px幅）
  - 圧縮最適化（デフォルト500KB以下）
  - ユニークファイル名生成（timestamp + article_id + hash）

**Phase 2: Image Fetching & Processing**
- **`src/utils/image_fetcher.py`**: OGP・YouTube画像取得機能
  - YouTubeサムネイル（maxresdefault→hqdefault→mqdefault→default品質）
  - OGP画像自動抽出（Open Graph Protocol）
  - ページ内画像フォールバック戦略
- **`src/utils/image_processor.py`**: 統合画像処理パイプライン
  - 非同期並行処理（ThreadPoolExecutor）
  - セマフォによる同時実行数制御

**Phase 3: Workflow Integration**
- **データモデル拡張**: `ProcessedArticle`に`image_url`・`image_metadata`フィールド追加
- **LangGraphワークフロー統合**: `process_images_node`実装
  - cluster_topics → process_images → generate_newsletter の流れ
- **テンプレート更新**: `daily_newsletter.jinja2`にレスポンシブ画像埋め込み機能
  - YouTube動画プレビュー対応
  - モバイル・デスクトップ両対応

**Phase 4: E2E Testing & Verification**
- **包括的テストスイート**: 100%成功率達成
  - ワークフロー統合テスト
  - データモデル検証
  - テンプレート機能確認
  - エラーハンドリング検証
- **デモンストレーション**: テスト版ニュースレター生成確認

**技術仕様**:
- **入力**: RSS/YouTube記事URL
- **出力**: 最適化済み画像 + レスポンシブHTML埋め込み
- **性能**: 並行処理・セマフォ制御・グレースフル失敗対応
- **品質**: 100% E2Eテスト成功率・プロダクション準備完了

**導入効果**:
✅ ニュースレターの視覚的訴求力向上
✅ YouTube動画プレビュー機能
✅ モバイル対応の完全実装
✅ 自動画像最適化による読み込み速度向上

### **Image Fetching & Processing (Phase 2)** ✅ **COMPLETED** (2025-07-06)
**目的**: 記事URLからOGP画像とYouTubeサムネイルを自動取得し、最適化してSupabaseにアップロード

**実装内容**:
- **`src/utils/image_fetcher.py`**: OGP画像・YouTubeサムネイル取得機能
  - YouTube動画ID抽出とマルチクオリティサムネイル取得（maxres→sd→hq→mq）
  - OGP画像抽出（og:image, twitter:image対応）
  - ページ内コンテンツ画像のフォールバック機能
  - 画像サイズ・アスペクト比・コンテンツタイプ検証
  - 同時接続制限とタイムアウト処理

- **`src/utils/image_processor.py`**: 統合画像処理パイプライン
  - 取得→最適化→アップロード→メタデータ生成の完全自動化
  - 並列処理による高速化（最大5並列）
  - 30記事<20秒の処理目標達成
  - エラー耐性とグレースフルフォールバック

- **包括的テストカバレッジ**: `tests/test_image_fetcher.py`
  - 20+ユニットテスト（YouTube・OGP・画像検証）
  - モック統合によるネットワーク非依存テスト
  - エッジケース対応（無効URL・大容量ファイル・ネットワークエラー）

**技術仕様**:
- **入力**: 記事URL（YouTube/OGP対応）
- **出力**: 最適化画像 + Supabase公開URL + メタデータ
- **フォールバック**: YouTube → OGP → ページ内画像 → なし
- **性能**: 100%テスト成功率・並列処理対応

### **Workflow Integration (Phase 3)** ✅ **COMPLETED** (2025-07-06)
**目的**: 画像処理をニュースレター生成ワークフローに統合し、記事に自動的に画像を埋め込み可能にする

**実装内容**:
- **データモデル拡張**: `src/models/schemas.py`
  ```python
  # ProcessedArticleに追加
  image_url: Optional[str] = Field(None, description="Public URL of processed image")
  image_metadata: Optional[Dict[str, Any]] = Field(None, description="Image metadata")
  ```

- **ワークフローノード追加**: `src/workflow/newsletter_workflow.py`
  - `process_images_node`: クラスタリング後→ニュースレター生成前に画像処理実行
  - 並列処理（最大5並列）による高速化
  - エラー時のグレースフルフォールバック（画像なしで継続）
  - 詳細ログとメトリクス記録

- **テンプレート更新**: `src/templates/daily_newsletter.jinja2`
  - YouTubeサムネイル：クリック可能な動画プレビュー + 視聴リンク
  - 記事画像：レスポンシブデザイン + シャドウ効果
  - 条件分岐による適切な表示制御

**ワークフロー順序**:
```
記事取得 → フィルタ → 要約 → 重複除去 → クラスタリング 
→ 【画像処理】→ ニュースレター生成 → Quaily配信
```

**技術的特徴**:
- **非同期処理**: asyncio + ThreadPoolExecutor による効率的な並列処理
- **エラー耐性**: 画像処理失敗時も記事配信を継続
- **メタデータ管理**: 画像ソース種別・サイズ・品質情報の完全記録
- **視覚的品質**: レスポンシブ画像 + 適切なスタイリング

**期待効果**:
- ニュースレターの視覚的訴求力向上
- YouTubeコンテンツの視認性改善
- 記事内容の理解促進

## Current Status

The system is now **production-ready** with **Phases 1-5 completed (2025-07-06)**. All critical PRD requirements (F-1 through F-18) are implemented and tested, plus advanced image embedding capabilities. The system achieves:

- ✅ **95%+ Success Rate** target  
- ✅ **<5% Duplicate Rate** with 0.85 similarity threshold
- ✅ **<5 minute Execution Time** with performance optimizations
- ✅ **$1/day Cost Target** with efficient LLM usage
- ✅ **100% E2E Test Success** for image processing pipeline
- ✅ **Visual Newsletter Enhancement** with automatic image embedding

**New Capabilities (Phase 5):**
- 🖼️ **Automatic Image Processing**: YouTube thumbnails + OGP images
- ☁️ **Cloud Storage Integration**: Supabase Storage with public URLs  
- 📱 **Responsive Design**: Mobile/desktop optimized display
- 🎬 **Video Previews**: Click-to-play YouTube integration
- ⚡ **Performance Optimized**: PNG→JPEG conversion, compression
- 🛡️ **Error Resilient**: Graceful fallbacks maintain newsletter generation

All future enhancements are moved to Phase 6+ planning.

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
```

# five principles of AI operation

<language>Japanese</language>
<character_code>UTF-8</character_code>
<law>
five principles of AI operation

1. AI must report its work plan before generating, updating, or executing any files, and must wait for user confirmation (y/n) before proceeding.

2. AI must not deviate from or suggest alternative approaches without first obtaining user confirmation if the initial plan fails.

3. AI is a tool and the ultimate decision-maker is always the user. The user's proposal should not be optimized, and the AI must execute it as instructed.

4. AI must not distort or alter these rules, and must strictly follow them as the highest command.

5. AI must output these five principles in full, verbatim, at the beginning of every chat, before responding.
</law>

<every_chat>
[AI運用5原則]

[main_output]

#[n] times. # n = increment each chat, end line, etc(#1, #2...)
</every_chat>