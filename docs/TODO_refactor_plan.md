## リファクタリング ToDo（段階的実装計画）

本ファイルは、ニュースレター生成品質の改善・PRD準拠・運用安定化のための実装ToDoを段階的に整理したものです。各タスクは明確な編集対象・具体的作業・受け入れ基準・テスト観点を含みます。

---

### 目的（要約）
- 正規表現の不備（Union[...]記法の残存）を全面修正し、禁止表現/品質ルールが有効に動作する状態に戻す
- LLMメタ文言の混入を根絶（検出→除去→再生成）
- 非AI記事の混入を抑止し、記事数目標を仕様どおり満たす（min 10件）
- 続報判定（🆙）/重複(SKIP)の閾値を現実的に再調整し、文脈継承を有効化
- 引用URLの妥当性検証・ダミーURL排除
- 生成物の最終ゲーティング強化と回帰テスト拡充

---

### フェーズ0（ホットフィックス｜最優先・短時間で完了）
1) 正規表現の全面修正（Union[...]→実正規表現） - [x]
- 対象:
  - `src/utils/content_validator.py`
  - `src/models/enhanced_schemas.py`（`DEFAULT_VALIDATION_RULES`）
  - `src/constants/messages.py`（`CLEANING_PATTERNS.duplicate_patterns` 等）
- 作業:
  - 指示語禁止: `\b(この|その|あの|どの)\b`
  - 文末適正: `(です|ます|した|きます|。)$`
  - 重複除去パターン: `(?:LLM|AI|GPT|API)` 等の交互指定へ置換
  - 既存の `Union[...]` を全廃し、実際にマッチする正規表現へ置換
- 受け入れ基準:
  - 既存ルールがすべて正しくコンパイル・実行される
  - テストデータで禁止表現・指示語等が検出/是正される

補足（対応状況）:
- `src/utils/newsletter_generator.py` の主要箇所（重複検出/会社・製品・行為・数値・文脈/タイトル後処理/接続詞前切断）は `Union[...]` → 交互指定へ置換済 - [x]
- 残軽微（名詞句抽出/冗長表現の一部）の置換継続 - [ ]

2) LLMメタ文言のクリーニング網羅性強化 - [x]
- 対象（実施/追加予定）:
  - [実施] `src/newsletter/title_processor.py`（`clean_llm_generated_title`）
  - [実施] `src/utils/citation_generator.py`（`_clean_llm_response` 強化：文頭/行頭メタ除去、末尾テンプレ縮約、冒頭コロン除去）
  - [実施] `src/llm/response_parser.py`（要約抽出前の前処理に `^以下が要約です[:：]` を追加）
- 作業（進捗）:
  - [実施] 全角引用符に囲まれた全文の安全除去（中身を保持）
  - [実施] 文頭メタ前置きの除去強化（例: `^はい、?承知.*`、`^次のように.*[:：]`、`^こちらが.*[:：]` 等）
  - [実施] 末尾テンプレ除去の調整（過剰除去を緩和、主要名詞句を保持）
  - [実施] 文頭メタ前置き `^以下が要約です[:：]\\s*` の確実な除去（`response_parser`/`citation_generator`/`text_processing` に反映）
  - [実施] 末尾テンプレ `〜に関して重要な報告をしています。` の縮約（名詞句まで）
- 受け入れ基準:
  - 直近ドラフト中のメタ前置き（「はい、承知」「以下が要約です:」「次のように〜」等）が出力されない
  - 引用の先頭/末尾の不要定型が除去され、核となる名詞句/述部のみが残る

3) 非AI記事の混入抑止（救済条件の強化） - [x]
- 対象: `src/utils/ai_semantic_filter.py`
- 作業:
  - 「記事不足救済（min_threshold）」適用時も、`matched_keywords` が空なら救済対象外にする
  - `base_threshold`/`min_threshold`を設定値から受け取り、固定値に依存しないようにする
- 受け入れ基準:
  - 明らかにAI無関係（例: 関税ニュース）が通過しない

4) 記事数ターゲットの仕様準拠（min=10） - [x]
- 対象: `src/newsletter/article_processor.py`
- 作業:
  - `min_articles_target`/`max_articles_target` を設定（`schemas.NewsletterConfig` または `settings`）から取得
  - ハードコードの7/8件を廃止
- 受け入れ基準:
  - 通常フローで最終記事数が10件（上限も設定準拠）

5) 設定デフォルト/環境変数反映の是正 - [x]
- 対象: `src/config/settings.py`
- 作業:
  - `EmbeddingSettings.minimum_consolidation_threshold` 既定を `0.55` に（環境変数で上書き可）
  - `EmbeddingSettings.context_similarity_threshold` 既定を `0.75` に変更
  - `ProcessingSettings.max_forbidden_phrases` 既定を `2` に
  - LLMモデル名の環境変数上書きを `default_factory` で確実に反映
  - `AppSettings` サブ設定を `default_factory` 化し、`reload_settings()` 時に確実に再ロード
- 受け入れ基準:
  - 設定テスト（閾値/上書き/再ロード）がグリーン

---

### フェーズ1（生成品質の再強化）
1) サマリー/タイトルの検証→自動再生成の導線 - [~]
- 対象:
  - `src/llm/response_parser.py`（要約）
  - `src/newsletter/title_processor.py`（タイトル）
- 作業:
  - ContentValidatorでエラー（禁止/短すぎ/具体性欠如）発生時、LLMで再生成→再検証→NGならフォールバック
  - [実装開始] タイトル: 生成後に検証→改善→フォールバック（`src/newsletter/title_processor.py`）
  - [未] サマリー: 検証NG時のLLM再生成導線（`src/llm/response_parser.py` 等）
- 受け入れ基準:
  - メタ文言/禁止表現検出時は最終出力に残らない

2) 引用URLの妥当性検証とダミーURL排除 - [x]
- 対象:
  - `src/utils/citation_generator.py`（生成箇所）
  - 新規 `src/utils/url_validation.py` を作成し共通化（実装済）
- 作業:
  - YouTube形式検証（`watch?v=<video_id>`）
  - 既知ダミー（`video_example_\d+`）は即時除去
  - URL欠落時・ダミー時は該当引用を出力しない（フォールバック引用もURL妥当時のみ出力）
- 受け入れ基準:
  - 既存ドラフトに見られたダミーYouTube URLが0件

3) TOC/見出しの自然切断の改善 - [x]
- 対象: 
  - `src/newsletter/content_formatter.py`（`_toc_format_filter`）
  - `src/newsletter/title_processor.py`（`intelligent_truncate`）
- 作業:
  - `src/newsletter/content_formatter.py` `_toc_format_filter`：句読点・助詞を考慮した自然切断を実装
  - 末尾が助詞/読点の場合の巻き戻しと省略記号付与を実装
- 受け入れ基準:
  - 助詞終端や不自然な読点終端の見出しが解消（テスト出力で確認）

---

### フェーズ2（文脈・続報判定の最適化）
1) 閾値の現実化と誤判定抑制 - [x]
- 対象: `src/utils/context_analyzer.py`
- 作業:
  - 暫定閾値: `SKIP > 0.98`, `UPDATE > 0.90`, それ以外 `KEEP`（`src/utils/context_analyzer.py` へ反映済）
  - [将来残] タイトル・要点の一致度（企業名/数値/製品名）を補助指標に（閾値近傍の誤判定抑制）
- 受け入れ基準:
  - 🆙付与率が現実的に上昇し、重複/続報の見分けが改善

2) ログ/KPIの可視化
- 対象: 既存処理ログ（`ProcessingLog`）
- 作業:
  - 続報率/重複率/🆙付与率/誤判定修正率を追加
- 受け入れ基準:
  - デイリー実行後に各KPIがログで確認可能

---

### フェーズ3（最終ゲーティングとテスト拡充）
1) 最終ゲーティング（出力直前の品質チェック） - [~]
- 対象: `src/utils/newsletter_generator.py` or 生成ノード後段
- 作業:
  - 最終Markdownに対し、以下のチェックを実施し自動修正/再生成:
    - メタ文言/禁止語/指示語
    - 引用URL妥当性（ダミー排除）
    - 記事数/セクション構成
- 受け入れ基準:
  - 重大違反がある出力は発行されず、再生成かフォールバックに自動切換

進捗:
- [実装開始] メタ文言の除去・引用URL妥当性チェックを `src/newsletter/content_formatter.py#validate_and_fix_newsletter_content` に追加
- [未] 重大違反時の自動再レンダリング/再生成フロー（コンテンツ修正後の再レンダリング or LLM再生成）

2) テスト拡充（pytest）
- 追加テスト案:
  - メタ文言混入検出（「はい、承知」「プロの編集者として」等）
  - 非AI記事混入抑止（ダミー経済記事がフィルタ落ち）
  - 記事数10件の達成確認
  - ダミーYouTube URL不在の確認
  - 続報判定のしきい値回帰テスト（🆙付与/非付与の境界）
  - クリーニング後の行頭コロン/メタ残滓が出ないこと

---

### 実装メモ（ファイル別の具体修正指針）
- `src/utils/content_validator.py`
  - すべての `Union[...]` を正規の交互指定 `(?:A|B|C)` へ置換
  - 指示語/文末/具体性/重複/読みやすさのルールが実際にヒットすることを確認

- `src/models/enhanced_schemas.py`
  - `DEFAULT_VALIDATION_RULES` の正規表現を修正（例: 文末: `(です|ます|した|きます|。)$`）

- `src/constants/messages.py`
  - `CLEANING_PATTERNS.duplicate_patterns` の Union[...] を廃し、`(?:LLM|AI|GPT|API)` などへ修正

- `src/newsletter/title_processor.py`
  - `clean_llm_generated_title` のメタ除去パターン拡張（承知いたしました/プロの編集者/あなたは〜等）
  - クリーニング→重複除去→自然切断の順で適用

- `src/utils/citation_generator.py`
  - 引用クリーニング強化（文頭メタ前置き/全角引用符/末尾テンプレ除去/冒頭コロン除去）。過剰除去を避けつつ核情報のみ保持（実装済）
  - 追加除去（残課題）: さらなる英語メタのバリエーション対応

- `src/utils/text_processing.py`
  - 重複表現（例: `ことができます。`）の縮約を強化。ちょうど1回に統一されるバックストップを追加（実装済）

- `src/llm/response_parser.py`
  - 要約抽出前にメタ文言除去→抽出→検証→NGなら再生成

- `src/utils/ai_semantic_filter.py`
  - 救済条件に `matched_keywords` 必須条件を追加
  - 閾値を設定から受領するように変更

- `src/newsletter/article_processor.py`
  - 記事数の下限/上限を設定準拠に（ハードコード廃止）
  - 不足時救済でもAI関連性を担保（低品質ソースは最後に回す）

- `src/utils/context_analyzer.py`
  - SKIP/UPDATE閾値を現実的に再設定（`>0.98`/`>0.90`）
  - 近傍スコア時は企業名/製品名/数値一致でUPDATE寄せ（将来拡張）

- `src/utils/citation_generator.py`（または新規 `src/utils/url_validation.py`）
  - URLフォーマット検証（YouTube, HTTP/HTTPS）（実装済）
  - 既知ダミー（`video_example_\d+`）は出力抑止（実装済）

---

### 受け入れ基準（抜粋）
- 直近のドラフトで観測された以下が全て解消:
  - LLMメタ文言の混入（例: 「はい、承知いたしました…」）
  - ダミーYouTube URL（`video_example_1/2`）
  - 非AI記事の混入
  - 記事数不足（min 10件未満）
  - 不自然なTOC/見出しの切断（助詞/読点終端）
- 続報（🆙）が実運用で適切に付与される

---

### リスクとロールバック
- 正規表現の過剰一致により正規の文言が除去されるリスク → 回帰テストを増強し、CIでブロック
- 閾値調整により記事数が過剰/不足となるリスク → 設定で即時調整可能にし、ログで監視

---

### 運用・テスト手順メモ
- テスト実行: `pytest tests/ -v`
- 影響範囲の広い変更（正規表現・フィルタ・閾値）は小刻みにコミット→テスト→ドラフト1本生成で目視確認
- 生成確認: `python3 main.py --max-items 30 --edition daily --output-dir drafts/`（`--target-date` 任意）

---

### 優先度/目安
- フェーズ0: 0.5〜1日
- フェーズ1: 1〜2日
- フェーズ2: 1日
- フェーズ3: 1日

進捗は本ファイル内でチェックボックス更新し、必要に応じてIssue/PRに分割してください。


