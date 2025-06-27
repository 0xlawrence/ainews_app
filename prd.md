# プロダクト要求仕様書 (PRD)

## 0. メタ情報
- **プロダクト名**: AI News v2 (Codename: "Hokusai")
- **作成日**: 2025-06-21
- **作成者**: Lawrence ＆ AI Assistant
- **関連プロジェクト**: 10_personal/projects/podcast2newsletter/
- **参照テンプレート**: 6_templates/pm/prd_template.md

---

## 1. 背景・課題

* RSS + YouTube の最新 AI ニュースを自動収集
* LLM 要約＋重複除去で日本語 3-4項目の箇条書きサマリー生成
* Markdown 形式でニュースレターを出力
* Quaily CLI を用いて Quaily プラットフォームへ API 入稿 (無料枠)

を日次で安定運用できる軽量アーキテクチャを構築する。

---

## 2. 目標 (SMART)
| # | 指標 | 目標値 | 計測方法 |
|---|------|-------|-----------|
| 1 | 生成成功率 | 95% 以上 | GitHub Actions 成功率 |
| 2 | サマリー指示語混入率 | 0% | pytest 正規表現検査 |
| 3 | 重複ニュース混入率 | <5%/週 | Supabase duplicate
events |
| 4 | 実行時間 | < 5 分/日 | GHA ジョブ時間 |
| 5 | LLM API コスト | < $1/日 | OpenAI Usage API |

---

## 3. ユースケース / ユーザーストーリー
* **読者 (AI/ML 業界関心層)** として、最新 AI 動向を 3 分で把握したい。
* **編集者 (Lawrence)** として、文章を手修正する余裕が無い日でも質の高いニュースレターが自動で下書きに入っていて欲しい。
* **SNS 拡散担当** として、ニュースレター公開後に X スレッドをワンクリックで生成したい (M2 以降)。

---

## 4. スコープ (MVP)
### In‐Scope
1. **ソース取得**  
   * 既存 RSS 一覧 (content_sources テーブル) と YouTube Channel ID から最新 24h 分を取得
2. **フィルタ & スコアリング**  
   * AI 関連キーワード簡易判定 (タイトル + Description)
3. **LLM 要約 (Gemini 2.5 Pro ⇒ Claude 3.7 Sonnet ⇒ GPT-4o-mini)**  
   * 3項目の箇条書き / 各項目200字程度 / 指示語禁止
4. **重複除去**  
   * 過去 7 日間のニュースと Jaccard+SequenceMatcher で比較
5. **トピッククラスタリング & 補強引用**  
   * 当日分の記事を Embedding + FAISS でクラスタリングし代表記事を選択。最大 3 件の引用ソースを抽出し Markdown 引用ブロックに差し込む
6. **過去記事文脈反映システム**
   * Embedding類似検索による過去記事との関係性判定とUPDATE処理
7. **Markdown ニュースレター生成 (Jinja2)**
8. **ローカル drafts ディレクトリへの出力**
9. **Supabase へのログ記録** (processed_content / processing_logs / contextual_articles)
10. **GitHub Actions 定期実行 (09:00 JST 日次)**

### Out-of-Scope (将来拡張)
* Slack通知機能 (Phase 4で実装)
* Quaily CLI 自動入稿 (Phase 4で実装)
* Supabase pgvector への移行 (Phase 5で検討、MVP はローカル FAISS)
* OGP 画像自動生成 (Phase 5)
* Quaily 有料 Premium API 等の拡張 (Phase 5)
* X / Threads 拡散フロー (Phase 5)

---

## 5. Functional Requirements
| ID | 要件 |
|----|------|
| F-1 | RSS & YouTube から最大 30 件取得し `source_type` 別に正規化 |
| F-2 | タイトル・説明に AI キーワードが含まれない記事は除外 |
| F-3 | Gemini 2.5 Pro を第一候補とし、失敗時 Claude 3.7 Sonnet、最終 fallback に GPT-4o-mini を用いて日本語 3-4項目の箇条書きサマリー生成。NG ワードは正規表現で除去 |
| F-4 | 過去 7 日データと Jaccard >0.7 または SequenceRatio >0.85 は重複と判定し SKIP |
| F-5 | 上位 10 件までをニュースレター本文に整形し Markdown 出力 |
| F-6 | Supabase `processed_content` へ upsert、`processing_logs` へ処理ログを残す |
| F-7 | 生成されたMarkdownニュースレターを `drafts/YYYY-MM-DD_newsletter.md` として保存し、手動確認可能な状態で出力 |
| F-8 | GitHub Actions ワークフローで `python main.py --max-items 30 --edition daily` を日次09:00 JST実行 |
| F-9 | 失敗時は標準エラー出力とログファイルに記録。GitHub Actions の実行ログで確認可能 |
| F-10 | LangGraph ワークフロー定義ファイル `workflow.yaml` を作成し、各ノードの再利用を容易にする |
| F-11 | LLM 呼び出しは `llm_router.invoke(task="summary")` で **Gemini → Claude → GPT-4o** のフォールバック 3 段階を実装 |
| F-12 | FAISS index ファイル `data/faiss/index.bin` を Git LFS で管理し、Phase-2 で Supabase へ移行 <br/>※ ローカル開発 (macOS/Windows) では **FAISS をインストールしなくても** `EmbeddingManager` が scikit-learn のコサイン類似度フォールバックで動作するため、依存エラーを回避可能 |
| F-13 | Playwright Chromium を GitHub Actions キャッシュし、OGP ジョブの実行時間を 30 秒以内に抑える |
| F-14 | Prompt 定義は `prompts/*.yaml` で管理し、LangSmith run-id を processing_logs に記録 |
| F-15 | 当日分の記事を Embedding+FAISS でクラスタリングし、代表記事を選択。同一クラスタの関連記事（RSS/YouTube）から最大3件を引用ブロックとして抽出し、実際の記事タイトル・URL で `>` ブロックに差し込む。要約は **3-4項目の箇条書き** とし、pytest で項目数・引用数を検証 |
| F-16 | **過去記事文脈反映システム**: 各ニュース候補を過去7日間の配信済み記事とEmbedding類似検索で照合。類似記事が見つかった場合、LLMが「SKIP（重複）」「UPDATE（続報として文脈反映）」「KEEP（独立記事）」を判定。UPDATE判定時は過去の経緯を踏まえた要約に自動修正し、関連する過去記事へのリンクを付与。続報記事の見出しには末尾に🆙絵文字を付与 |
| F-17 | **文脈継承データベース**: Supabase `contextual_articles` テーブルに記事間の関係性（続報、関連トピック、シリーズ）を記録。記事生成時に関連記事チェーンを自動構築し、「【続報】」「【関連】」タグと過去記事リンクを自動付与 |
| F-18 | `--target-date YYYY-MM-DD` オプションで任意の日付のみを対象にニュースレターを生成できる |

---

## 6. Non-functional Requirements
| 区分 | 内容 |
|------|------|
| パフォーマンス | 30 件処理で 3 分以内 (並列化実装後、従来比40-50%短縮) |
| 可観測性 | `logs/` に構造化 JSON ログ、Supabase processing_logs に永続化 |
| 信頼性 | LLM 失敗時は Retry×2 → fallback_simple_summary |
| コスト | 月 $30 以内 (OpenAI+Supabase) |
| セキュリティ | API Key は GitHub Secrets 管理。RLS で anon role は読み取りのみ |

---

## 7. システム構成 (概略)
```
┌──────────────┐      ┌─────────────────┐
│   GitHub      │ cron │    main.py      │
│  Actions      │─────▶│   (Python)      │
└──────────────┘      │  ├─ fetch RSS   │
                       │  ├─ fetch YT   │
                       │  ├─ filter     │
                       │  ├─ LLM     │
                       │  ├─ dedup      │
                       │  ├─ render MD  │
                       │  ├─ write DB   │
                       │  └─ call Quaily│
                       └──────┬──────────┘
                              │
          Supabase (processed_content / logs)        Quaily Platform
```

### 7.1 データベース設計（文脈継承対応）

**contextual_articles テーブル**
```sql
CREATE TABLE contextual_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id VARCHAR NOT NULL,
  title TEXT NOT NULL,
  content_summary TEXT NOT NULL,
  embedding VECTOR(1536), -- OpenAI text-embedding-3-small
  published_date TIMESTAMP NOT NULL,
  source_url TEXT,
  topic_cluster VARCHAR,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE article_relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_article_id UUID REFERENCES contextual_articles(id),
  child_article_id UUID REFERENCES contextual_articles(id),
  relationship_type VARCHAR NOT NULL, -- 'sequel', 'related', 'update'
  similarity_score FLOAT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 7.2 文脈判定プロンプト設計

**prompts/context_analysis.yaml**
```yaml
context_analysis_prompt: |
  与えられた"今回のニュース"と"過去類似ニュース"を比較し、以下の結果を返すこと。
  
  - 過去のトピックと完全に重複なら"SKIP"
  - 一部更新が必要なら"UPDATE" 
    - 例：過去の類似トピックの続報、新展開、追加情報
    - この場合、過去の文脈を踏まえた修正要約も返すこと
  - 問題なければ"KEEP"
  
  # 今回のニュース
  {current_news}
  
  # 過去類似ニュース（関連度順）
  {past_related_news}
  
  # 出力形式
  {
    "decision": "SKIP|UPDATE|KEEP",
    "reasoning": "判定理由",
    "contextual_summary": "過去の文脈を反映した要約（UPDATEの場合のみ）",
    "references": ["関連する過去記事のID"]
  }
```

### 7.3 実装アーキテクチャ例

```python
class ContextualSummarySystem:
    def __init__(self):
        self.embedding_model = "text-embedding-3-small"  # OpenAI
        self.faiss_index = faiss.IndexFlatIP(1536)  # コサイン類似度
        self.past_articles_db = []  # 過去記事のメタデータ
    
    def find_related_articles(self, current_article, top_k=4):
        """現在の記事に関連する過去記事を検索"""
        current_embedding = self.get_embedding(current_article['title'] + current_article['content'])
        distances, indices = self.faiss_index.search(current_embedding, top_k)
        return [self.past_articles_db[i] for i in indices[0]]
```

### 7.4 コードベースアーキテクチャ（リファクタリング後）

**定数管理の集約化**
```
src/constants/
├── __init__.py              # 定数パッケージ定義
├── mappings.py              # 企業・製品・ソース名マッピング統一管理
├── settings.py              # 数値設定とアプリケーション定数
└── messages.py              # エラーメッセージとデフォルト文言
```

**共通ユーティリティ**
```
src/utils/
├── text_processing.py       # 日本語処理共通ユーティリティ
├── citation_generator.py    # 引用生成（定数参照に更新）
├── newsletter_generator.py  # ニュースレター生成（定数参照に更新）
└── ... (他の既存ファイル)
```

**パフォーマンス最適化**
- **並列LLM処理**: `check_duplicates_node_parallel()` で記事処理を8並列化
- **Citation並列生成**: `enhance_articles_with_citations_parallel()` で引用を並列生成
- **設定集約**: 並列数、閾値、制限値をすべて`settings.py`で一元管理

**品質向上項目**
- **定数統一**: 企業名・製品名マッピングの重複排除
- **メッセージ集約**: エラーメッセージとフォールバック文言の一元管理
- **テキスト処理共通化**: 日本語正規化処理の関数化
- **マジックナンバー排除**: ハードコードされた数値の定数化

**期待効果**
- **パフォーマンス**: 3記事145秒 → 60-80秒（40-50%短縮）
- **保守性**: 1箇所の定数変更ですべてに反映
- **一貫性**: 企業名・製品名の表記統一
- **可読性**: コードの意図が明確化

---

## 8. 実装フェーズ定義

### **Phase 1: 基盤システム構築**
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

**成果物**: 
- 最小限の機能でニュースレター生成が可能
- 日次実行が安定動作

**技術検証**:
- LLM API の安定性とコスト確認
- Supabase 接続とクエリ性能

---

### **Phase 2: 文脈反映システム実装**
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

**成果物**:
- 過去記事を考慮した文脈反映要約
- 続報記事の自動判定と適切なフォーマット

**技術検証**:
- Embedding検索の精度とパフォーマンス
- 文脈判定の品質評価

---

### **Phase 3: 品質保証・自動化強化**
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

**成果物**:
- 高品質で一貫したニュースレター出力
- 包括的なテストカバレッジ
- 運用監視機能
- 保守性・パフォーマンス・一貫性が向上したコードベース

**技術検証**:
- 並列化によるパフォーマンス最適化（40-50%短縮確認）
- エラー率とリカバリー機能の確認
- 定数管理とコード品質の向上確認

---

### **Phase 4: Quaily統合・配信自動化**
**目標**: 完全自動配信システムの確立

**実装項目**:
- [x] Quaily CLI 統合とテスト
- [x] drafts から Quaily への自動入稿機能
- [x] 配信前プレビュー機能
- [x] 配信履歴管理
- [x] バックアップ・リカバリ機能
- [x] 配信失敗時の自動リトライ
- [x] Slack通知機能（配信成功・失敗の通知）
- [x] 配信成功率監視

**成果物**:
- 完全自動化されたニュースレター配信
- 安定した日次運用

**技術検証**:
- Quaily API の安定性確認
- 配信成功率95%以上の達成

---

### **Phase 5: 拡張機能・最適化**
**目標**: 追加価値機能と長期運用最適化

**実装項目**:
- [ ] OGP画像自動生成（Playwright + HTML/CSS）
- [ ] Supabase pgvector 移行検討
- [ ] 配信時間最適化
- [ ] A/Bテスト機能（プロンプト・フォーマット）
- [ ] 読者フィードバック収集機能
- [ ] パフォーマンス監視強化
- [ ] コスト最適化
- [ ] ログ分析ダッシュボード（Supabase）

**成果物**:
- 視覚的に魅力的なニュースレター
- データドリブンな品質改善サイクル

**技術検証**:
- 長期運用での安定性確認
- ROI 最適化

---

## 9. リスク & 対策
1. **LLM API 変動** → fallback_simple_summary / モデル切替オプション
2. **Supabase 自動 Pause** → heartbeat ワークフロー
3. **RSS ソース停止** → content_sources テーブルで容易に ON/OFF
4. **Quaily API 仕様変更** → quail-cli バージョンを pin ＆随時アップデート

---

## 10. 承認
| 役割 | 名前 | ステータス |
|------|------|------------|
| プロダクトオーナー | Lawrence | ☐ |
| テクニカルリード   | AI Assistant | ☐ |

---

## 11. 参考にしたベストプラクティス
この記事は [[11_zettelkasten/Literature/202504/AIニュースレターを支える技術.md]] の実装知見を踏まえて設計している。

| 採用元アイデア | 本プロダクトでの適用方法 |
|----------------|---------------------------|
| **LangGraph ベースのワークフロー実装** | Python 製 `langgraph` で「取得→要約→重複判定→レンダリング→投稿」のノードを定義し、状態遷移を図示可能にする。|
| **マルチ LLM フォールバック (Gemini→Claude→OpenAI)** | `llm_router.py` でモデル選択／リトライロジックを共通化し、要約・導入文・タイトル生成に再利用。|
| **FAISS + Embedding による重複排除** | Phase-2 で pgvector 導入まではローカル `faiss.IndexFlatIP` を利用。過去7日分のベクトルを保持し類似度>0.85 を重複判定。|
| **OGP 画像生成: LLM が HTML テンプレートを書き Playwright でスクショ** | Phase-2 機能として `ogp_generator.py` を追加。Gemini でテンプレ変数を埋め込み、Chromium headless でレンダリング。|
| **Structured Output (JSON Schema) で LLM 返却を検証** | Pydantic モデル `SummaryOutput` / `ContextAnalysisResult` で出力形式を厳密定義。LangChain Structured Output を活用し、不正な出力を事前防止 |

---

## 12. 技術実装詳細仕様

### 12.1 Structured Output実装（Pydantic）

**models/schemas.py**
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class NewsArticle(BaseModel):
    title: str = Field(..., max_length=150)
    source_url: str
    published_date: str
    content_summary: str

class SummaryOutput(BaseModel):
    summary_points: List[str] = Field(..., min_items=3, max_items=4)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    source_reliability: Literal["high", "medium", "low"]
    
    class Config:
        json_schema_extra = {
            "example": {
                "summary_points": [
                    "OpenAIがGPT-5の開発を発表、2025年後半リリース予定",
                    "推論能力が大幅向上、数学・科学分野での精度が50%改善",
                    "マルチモーダル機能強化、動画理解が可能に"
                ],
                "confidence_score": 0.85,
                "source_reliability": "high"
            }
        }

class ContextAnalysisResult(BaseModel):
    decision: Literal["SKIP", "UPDATE", "KEEP"]
    reasoning: str = Field(..., max_length=500)
    contextual_summary: Optional[str] = Field(None, max_length=1000)
    references: List[str] = Field(default_factory=list)
    similarity_score: float = Field(..., ge=0.0, le=1.0)
```

### 12.2 LangGraphワークフロー実装

**workflow/newsletter_workflow.py**
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class NewsletterState(TypedDict):
    raw_articles: List[dict]
    filtered_articles: List[dict]
    summarized_articles: List[dict]
    deduplicated_articles: List[dict]
    clustered_articles: List[dict]
    final_newsletter: str
    processing_logs: List[dict]

def create_newsletter_workflow():
    workflow = StateGraph(NewsletterState)
    
    # ノード定義
    workflow.add_node("fetch_sources", fetch_rss_youtube)
    workflow.add_node("filter_ai_content", filter_ai_keywords)
    workflow.add_node("generate_summaries", generate_llm_summaries)
    workflow.add_node("check_duplicates", check_duplicate_content)
    workflow.add_node("cluster_topics", cluster_similar_topics)
    workflow.add_node("generate_newsletter", render_markdown_newsletter)
    
    # エッジ定義
    workflow.add_edge("fetch_sources", "filter_ai_content")
    workflow.add_edge("filter_ai_content", "generate_summaries")
    workflow.add_edge("generate_summaries", "check_duplicates")
    workflow.add_edge("check_duplicates", "cluster_topics")
    workflow.add_edge("cluster_topics", "generate_newsletter")
    workflow.add_edge("generate_newsletter", END)
    
    workflow.set_entry_point("fetch_sources")
    return workflow.compile()
```

### 12.3 重複判定ロジック統一実装

**deduplication/duplicate_checker.py**
```python
import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from difflib import SequenceMatcher

class HybridDuplicateChecker:
    def __init__(self):
        self.embedding_model = "text-embedding-3-small"
        self.faiss_index = faiss.IndexFlatIP(1536)
        self.tfidf_vectorizer = TfidfVectorizer(max_features=1000)
        
    def check_duplicate(self, current_article: dict, past_articles: List[dict]) -> dict:
        """
        2段階重複チェック：
        1. 高速スクリーニング（TF-IDF + Jaccard）
        2. 精密判定（Embedding類似度）
        """
        # Stage 1: 高速スクリーニング
        potential_duplicates = self._fast_screening(current_article, past_articles)
        
        if not potential_duplicates:
            return {"is_duplicate": False, "method": "fast_screening"}
            
        # Stage 2: Embedding精密判定
        embedding_result = self._embedding_similarity_check(
            current_article, potential_duplicates
        )
        
        return embedding_result
    
    def _fast_screening(self, current: dict, past_articles: List[dict]) -> List[dict]:
        """Jaccard係数 + SequenceMatcher による高速スクリーニング"""
        candidates = []
        current_text = f"{current['title']} {current['content']}"
        
        for past_article in past_articles:
            past_text = f"{past_article['title']} {past_article['content']}"
            
            # Jaccard係数計算
            jaccard_score = self._jaccard_similarity(current_text, past_text)
            
            # SequenceMatcher計算
            sequence_ratio = SequenceMatcher(None, current_text, past_text).ratio()
            
            if jaccard_score > 0.4 or sequence_ratio > 0.6:  # 緩めの閾値でスクリーニング
                candidates.append({
                    **past_article,
                    "jaccard_score": jaccard_score,
                    "sequence_ratio": sequence_ratio
                })
        
        return candidates[:10]  # 上位10件のみEmbedding判定へ
    
    def _embedding_similarity_check(self, current: dict, candidates: List[dict]) -> dict:
        """Embedding類似度による精密重複判定"""
        current_embedding = self._get_embedding(f"{current['title']} {current['content']}")
        
        max_similarity = 0.0
        most_similar_article = None
        
        for candidate in candidates:
            candidate_embedding = self._get_embedding(
                f"{candidate['title']} {candidate['content']}"
            )
            
            similarity = np.dot(current_embedding, candidate_embedding)
            
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_article = candidate
        
        # 重複判定閾値
        if max_similarity > 0.85:
            return {
                "is_duplicate": True,
                "method": "embedding_similarity",
                "similarity_score": max_similarity,
                "duplicate_article": most_similar_article
            }
        
        return {"is_duplicate": False, "method": "embedding_similarity"}
```

### 12.4 エラーハンドリング・リトライ戦略

**utils/error_handler.py**
```python
import asyncio
import logging
from typing import Callable, Any, Optional
from functools import wraps

class LLMRetryHandler:
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.logger = logging.getLogger(__name__)
    
    def with_fallback(self, primary_model: str, fallback_models: List[str]):
        """LLMフォールバック付きデコレータ"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                models_to_try = [primary_model] + fallback_models
                
                for i, model in enumerate(models_to_try):
                    kwargs['model'] = model
                    
                    for attempt in range(self.max_retries):
                        try:
                            result = await func(*args, **kwargs)
                            
                            # 結果検証
                            if self._validate_llm_output(result):
                                self.logger.info(f"Success with {model} on attempt {attempt + 1}")
                                return result
                            else:
                                raise ValueError(f"Invalid output from {model}")
                                
                        except Exception as e:
                            wait_time = self.backoff_factor ** attempt
                            self.logger.warning(
                                f"Attempt {attempt + 1} failed for {model}: {str(e)}"
                            )
                            
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(wait_time)
                            else:
                                # 最後のモデルの最後の試行が失敗した場合
                                if i == len(models_to_try) - 1:
                                    return self._fallback_simple_summary(*args, **kwargs)
                                break  # 次のモデルへ
                
                return self._fallback_simple_summary(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def _validate_llm_output(self, output: Any) -> bool:
        """LLM出力の妥当性検証"""
        if not output:
            return False
            
        # Pydanticモデルの場合
        if hasattr(output, 'model_validate'):
            try:
                output.model_validate(output.model_dump())
                return True
            except Exception:
                return False
        
        # 文字列の場合の基本検証
        if isinstance(output, str):
            forbidden_phrases = [
                "申し訳ございません", "すみません", "エラーが発生",
                "I apologize", "I'm sorry", "I cannot"
            ]
            return not any(phrase in output for phrase in forbidden_phrases)
        
        return True
    
    def _fallback_simple_summary(self, *args, **kwargs) -> dict:
        """全LLMが失敗した場合の簡易要約"""
        self.logger.error("All LLM attempts failed, using fallback summary")
        
        # 元記事のタイトルと最初の200文字を使用
        article = kwargs.get('article', {})
        title = article.get('title', 'タイトル不明')
        content = article.get('content', '')[:200] + "..."
        
        return {
            "summary_points": [
                f"【速報】{title}",
                f"詳細: {content}",
                "※自動要約が失敗したため、元記事をご確認ください"
            ],
            "confidence_score": 0.1,
            "source_reliability": "low",
            "fallback_used": True
        }

# 使用例
retry_handler = LLMRetryHandler(max_retries=3)

@retry_handler.with_fallback(
    primary_model="gemini-2.5-pro",
    fallback_models=["claude-3.7-sonnet", "gpt-4o-mini"]
)
async def generate_summary(article: dict, model: str) -> SummaryOutput:
    # LLM呼び出し実装
    pass
```

### 12.5 GitHub Actions実装詳細

**.github/workflows/newsletter.yml**
```yaml
name: Daily Newsletter Generation

on:
  schedule:
    - cron: '0 0 * * *'  # 09:00 JST (00:00 UTC)
  workflow_dispatch:  # 手動実行可能

jobs:
  generate-newsletter:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    
    steps:
    - uses: actions/checkout@v4
      with:
        lfs: true  # FAISS indexファイル用
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        cache: 'pip'
    
    - name: Cache FAISS Index
      uses: actions/cache@v3
      with:
        path: data/faiss/
        key: faiss-index-${{ hashFiles('data/faiss/metadata.json') }}
        restore-keys: faiss-index-
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        playwright install chromium
    
    - name: Generate Newsletter
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        CLAUDE_API_KEY: ${{ secrets.CLAUDE_API_KEY }}
        SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
        SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        LANGSMITH_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
      run: |
        python main.py --max-items 30 --edition daily --output-dir drafts/
    
    - name: Upload Newsletter Draft
      uses: actions/upload-artifact@v3
      with:
        name: newsletter-draft
        path: drafts/
    
    - name: Notify on Failure
      if: failure()
      uses: 8398a7/action-slack@v3
      with:
        status: failure
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
        text: "ニュースレター生成が失敗しました。ログを確認してください。"
```

### 12.6 レイアウト & 日本語最適化

| 変更点 | 実装箇所 | 効果 |
|---------|-----------|-------|
| 導入文を必ず 3 文構成で生成し、文ごとに改行 | `newsletter_generator._generate_lead_text` | 読みやすいリード文、要点が明確 |
| 目次・見出しを英語タイトルではなく **日本語要約タイトル** に置換 | `daily_newsletter.jinja2` | 一目で内容を把握しやすい |
| 目次行・見出し直後に空行を挿入 | `daily_newsletter.jinja2` | Markdown レンダリング時の改行欠落を防止 |
| アンカーリンク除去 | `daily_newsletter.jinja2` | ノイズ削減・可読性向上 |
| 箇条書き保証（3-4 行） & バリデーション | `SummaryOutput` スキーマ | 体裁崩れ防止 |
| 引用ブロックに日本語 1 行要約を追加、類似度 0.75 未満は除外 | `citation_generator` | 情報量を担保しつつ無関係記事を排除 |

### 12.7 品質ガードレール強化 (Phase 3完了)

| 層 | 目的 | 実装ポイント |
|----|------|--------------|
| 入力品質 | 無関係ソース・ダミーURL遮断 | AIContentFilter を Embedding ベースへ拡張、`quality_rank` ホワイトリスト適用 |
| LLM 出力 | JSON 逸脱・bullet不足を自己修正 | `StructuredOutputParser.with_retry()` + `ContentValidator` ERROR で自動リトライ |
| 出力前 | Markdown 生成直前に最終バリデーション | 不合格記事を SKIP、ジョブログ記録 |

### 12.8 重要な品質改善 (2025-06-24 完了)

| 問題 | 原因 | 解決策 | ステータス |
|------|------|--------|----------|
| Bay Area Timesの非関連引用 | 幅広ニュースソースのフィルタ不足 | AIキーワード3個以上+地政学除外強化 | ✅ 完了 |
| TOCタイトル中途切断 | テンプレートフィルタ重複適用 | 80文字バランス+文境界検出 | ✅ 完了 |
| 引用ブロック品質不均一 | 日本語要約長度制約不足 | 80-200文字強制+再生成ロジック | ✅ 完了 |
| Embeddingデータ変換エラー | 文字列形式ファイル処理不備 | JSON+evalフォールバック実装 | ✅ 完了 |

---

## 13. 出力サンプル（技術仕様準拠）

### 13.1 最終出力形式（drafts/2025-06-21_newsletter.md）

```markdown
# 2025年06月21日 AI NEWS TLDR

## リード文
### OpenAI o3進化とAltman氏の未来予測：急速に変化するAI業界の最新動向

OpenAIが高性能モデルo3-proをChatGPT Pro/TeamユーザーとAPIで提供開始し、同時に既存o3モデルの大幅値下げと利用枠倍増を発表しました。

一方、Sam Altman CEOは「穏やかな特異点」と題したブログで、AIが人間より知的なタスクを実行する未来を予測。また夏後半に予定するオープンウェイトモデルについては「予想外の素晴らしい成果」のため延期されています。

企業のAIエージェント開発も加速しており、メルカリのデータ分析AI「Socrates」構築やAlgomaticの炎上対策AIなど具体的な活用事例が続々と登場しています。

それでは各トピックの詳細を見ていきましょう。

## 目次
1. OpenAI GPT-5発表、推論能力が大幅向上
2. Google Quantum AI、量子優位性をAI学習に応用
3. Meta、オープンソースLLMの新戦略発表

---

## 1. OpenAI GPT-5発表、推論能力が大幅向上 🆙

- OpenAIがGPT-5の開発完了を発表、2025年後半の一般公開を予定すると発表しました
- 数学・科学分野での推論精度が前世代比50%向上、複雑な問題解決能力を大幅強化しているようです
- マルチモーダル機能が進化し、動画コンテンツの理解・生成が可能になります
- エンタープライズ向けAPIは2025年Q3から段階的提供開始するとされ、創作フローへ導入されるようになる見込みです

> **TechCrunch** (https://techcrunch.com/openai-gpt5-announcement): OpenAI announces GPT-5 with breakthrough reasoning capabilities
> 【翻訳】GPT-5は前世代比50％精度向上、複雑推論を実現。企業APIは2025年Q3開始予定

> **The Verge** (https://theverge.com/gpt5-multimodal-features): GPT-5's multimodal features could revolutionize content creation
> 【翻訳】強化されたGPT-5のマルチモーダル機能で動画理解・生成が可能、創作フローを革新

> **AI News Channel** (https://youtube.com/watch?v=xyz123): GPT-5 Demo: Solving Complex Mathematical Proofs
> 【翻訳】デモでGPT-5が高度な数学証明を自動生成し正当性を検証、研究応用の可能性示す

**関連記事**: [2025年06月15日: OpenAI GPT-4.5の性能評価結果](../2025-06-15_newsletter.md#gpt-45-performance)

---

## 2. Google Quantum AI、量子優位性をAI学習に応用

- Google Quantum AIチームが量子コンピューティングを活用したAI学習手法を発表しました
- 従来のGPUクラスターと比較して学習時間を90%短縮することに成功しています
- 特に大規模言語モデルの事前学習において顕著な効果を確認されたとのこと
- 2026年には商用量子AI学習サービスの提供を計画です

> **Nature AI** (https://nature.com/quantum-ai-breakthrough): Quantum advantage in machine learning training achieved
> 【翻訳】量子プロセッサでAI学習時間を90％短縮、精度維持した量子優位性を実証した

> **Google AI Blog** (https://ai.googleblog.com/quantum-ml-training): Scaling AI training with quantum processors
> 【翻訳】量子AI学習基盤を公開、単位コスト半減と大規模モデルへのスケール検証を報告します

---

## 3. Meta、オープンソースLLMの新戦略発表

- MetaがLlama 3.5シリーズの開発ロードマップを公開、完全オープンソース化を推進
- 商用利用制限を撤廃し、企業での自由な利用・改変を許可
- コミュニティ主導の開発体制を強化、月次でのモデル更新を実施予定
- OpenAI・Anthropicの商用モデルに対抗する無料代替案として位置づけ

> **Meta AI Research** (https://ai.meta.com/llama-3-5-announcement): Llama 3.5: Democratizing Advanced AI
> 【翻訳】Llama 3.5は商用制限撤廃し完全OSS化、毎月アップデートで協調開発を促進

---

### 13.2 処理ログ出力例（logs/newsletter_2025-06-21.json）

```json
{
  "processing_id": "newsletter_20250621_090000",
  "timestamp": "2025-06-21T00:00:00Z",
  "status": "SUCCESS",
  "execution_time_seconds": 247,
  "stages": {
    "fetch_sources": {
      "rss_articles": 23,
      "youtube_videos": 7,
      "total_fetched": 30,
      "duration_seconds": 45
    },
    "filter_ai_content": {
      "input_count": 30,
      "filtered_count": 18,
      "ai_relevance_threshold": 0.7,
      "duration_seconds": 12
    },
    "generate_summaries": {
      "input_count": 18,
      "successful_summaries": 15,
      "failed_summaries": 3,
      "llm_usage": {
        "gemini_success": 12,
        "claude_fallback": 2,
        "gpt4o_fallback": 1,
        "total_tokens": 45670
      },
      "duration_seconds": 156
    },
    "check_duplicates": {
      "input_count": 15,
      "duplicates_found": 3,
      "updates_applied": 1,
      "final_count": 12,
      "embedding_comparisons": 180,
      "duration_seconds": 23
    },
    "cluster_topics": {
      "input_count": 12,
      "clusters_formed": 3,
      "representative_articles": 3,
      "citations_added": 9,
      "duration_seconds": 8
    },
    "generate_newsletter": {
      "template": "daily_newsletter.jinja2",
      "output_file": "drafts/2025-06-21_newsletter.md",
      "word_count": 1247,
      "duration_seconds": 3
    }
  },
  "quality_metrics": {
    "summary_instruction_words": 0,
    "citation_count": 9,
    "bullet_points_per_topic": [4, 4, 3],
    "readability_score": 8.2
  },
  "costs": {
    "openai_embedding": 0.12,
    "gemini_api": 0.34,
    "claude_api": 0.08,
    "total_usd": 0.54
  },
  "langsmith_run_id": "run_abc123def456"
}