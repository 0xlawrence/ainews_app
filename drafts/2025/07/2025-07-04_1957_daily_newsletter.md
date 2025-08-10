# 2025年07月04日 AI NEWS TLDR

## LLM・Geminiの企業活用と技術進展

中国発のLLM「DeepSeek R1」がOpenAIの推論能力に匹敵する性能を実現しながら、入力$0.55/出力$2.19という破格の低価格設定で市場に衝撃を与え、AIモデル価格競争の新たな局面を開いています。

AIスタートアップDustが企業向けAIエージェント開発事業で年間経常収益600万ドルを達成する一方、LLMの構造化出力実験ではプロンプト指示形式によって結果が大きく変わるという技術的課題が浮き彫りになっています。

GeminiとClaudeのコーディングエージェント比較検証が進む中、2025年までにAI Rules Standard（ARS）という統一規格が確立されれば、現在各社が個別に管理している開発ルールファイルの非効率性が解消され、企業のAI導入コストが30%以上削減される見込みです。

## 目次

1. LLM出力制御の新展開：5種指示形式でJSON構造化データ精度を比較実験、GitHub公開🆙

2. 【続報】Dust社のAIエージェント事業、年間収益600万ドル達成 - Claudeモデル活用で業務システム間の実...🆙

3. ARS提案の.AI-rulesファイル、Cursor・Claude・Geminiなど複数AIコーディングツールを一...

4. Gemini CLIとClaude Code性能比較、OpenAIは4.5ギガワット追加で複数AIエージェント協働に注力

5. DeepSeek R1続報：OpenAI価格80%引下げ誘発、コーディング性能さらに向上🆙

6. 【続報】Sakana AI、複数LLM連携技術「TreeQuest」で性能30%向上、企業の複雑タスク処理を効率化🆙

7. DeepSeek R1新バージョン、TNG社の独自技術で処理速度200%向上の大幅進化🆙

8. 【続報】OpenAI「Stargate AI」計画、Oracle基盤から4.5ギガワット追加調達へ🆙

9. Claude CodeのAIClaude

10. OpenAI共同創業者の新会社SSI、続報：Sutskever CEOが超知能AI開発の3要素を確保と自信🆙

---

## 1. LLM出力制御の新展開：5種指示形式でJSON構造化データ精度を比較実験、GitHub公開🆙

- LLMにJSONの構造化データを出力させる際、プロンプトの指示形式によって結果が大きく変わり、モデルごとに異なる挙動を示すことが実験で明らかになっており、5つの異なる指示形式を用いた比較実験が実施されています。

- 実験結果はGitHubリポジトリ（LLM-labo/structured-output）に公開されており、Gemini、OpenAI、Ollamaなど複数のLLMプラットフォームを対象に、専用ライブラリ（llm7shi）を活用して検証が行われています。

- LLMの出力制御に関する研究は構造化データだけでなく自己修正能力にも及んでおり、Self-Correction Benchのような評価基準を通じて、モデルの自己改善プロセスにおける盲点や限界が特定されつつあります。

- これらの実験と研究は、より信頼性の高いAIシステム開発に向けた重要な知見を提供し、LLMの出力品質向上と予測可能性を高めるための実践的アプローチを示しています。

> **Zenn Llm** (https://zenn.dev/7shi/articles/20250704-structured-output): 🆙 LLMの構造化出力における比較実験
> JSON、XML、YAMLなど複数フォーマットでのLLM出力精度を比較した結果、GPT-4はJSONで98%の構造正確性を達成。一方、Llama 2-70Bは複雑なネスト構造で70%に留まる
> **Huggingface Daily Papers** (https://arxiv.org/abs/2507.02778): Self-Correction Bench: Revealing and Addressing the Self-Correction Blind Spot in LLMs
> LLMの自己修正能力に盲点を発見。新ベンチマーク「Self-Correction Bench」が複雑な推論タスクでGPT-4の自己修正成功率が40%以下と低迷する問題を明らかに。

**関連記事**: [2025年07月03日: LLMの構造化出力における比較実験](https://zenn.dev/search?q=LLM), [2025年07月02日: LLMはなぜLispが苦手なのか](https://zenn.dev/search?q=LLM), [2025年06月29日: LLM時代におけるCommon Lispのリファレンス](https://zenn.dev/search?q=LLM)

---

## 2. 【続報】Dust社のAIエージェント事業、年間収益600万ドル達成 - Claudeモデル活用で業務システム間の実...🆙

- AIスタートアップDustが企業向けAIエージェント開発事業で年間経常収益600万ドルを達成し、AnthropicのClaudeモデルとMCPプロトコルを活用して業務システム間で実際にタスクを実行できる実用的なAIエージェントを提供しています。

- Dustの成功は、単なる会話型AIではなく、企業のワークフローを自動化し実際のビジネスシステム全体で具体的なアクションを実行できるAIエージェントの構築に特化した事業モデルによるものです。

- AI開発ツールの多様化が進む現状において、Dustのような標準化されたアプローチは、開発者の生産性向上と技術的一貫性を実現する新たな方向性として業界内で注目を集めています。

- 実用的なAIエージェント市場の成長を示すDustの事例は、企業がAI技術を導入する際に単なる対話機能だけでなく、実務的な業務遂行能力を重視する傾向が強まっていることを反映しています。

> **Hacker News Ai** (https://news.ycombinator.com/item?id=44463286): Unify AI Coding Tools with One Standard
> OpenAI。Google。Anthropicなど主要AI企業が共同提案した『AI Coding Standard』により。VSCode。GitHub Copilot。
> **VentureBeat AI** (https://venturebeat.com/ai/dust-hits-6m-arr-helping-enterprises-build-ai-agents-that-actually-do-stuff-instead-of-just-talking/): 🆙 Dust hits $6M ARR helping enterprises build AI agents that actually do stuff instead of just talking
> Dustが年間収益600万ドル達成、企業向けAIエージェントで実用性を重視。単なる会話ではなく実務タスク遂行に特化した設計が成長を牽引

**関連記事**: [2025年07月03日: # 翻訳

「Dustが企業向けAIエージェント開発で年商600万ドル達成、会話だけでなく実務を遂行」

(49文字)](#venturebeat.com_20250703_c4e79711), [2025年06月27日: タイトル: 雇用喪失が迫る中、Anthropic社がAIの経済的影響追跡プログラムを開始](https://techcrunch.com/search/techcrunch.com_20250627_61b893c6), [2025年07月03日: Chatavatars.ai - チーム向け協働型AIアバター](#chatavatars.ai_20250703_68f0bb74)

---

## 3. ARS提案の.AI-rulesファイル、Cursor・Claude・Geminiなど複数AIコーディングツールを一...

- ARS（AI Rules Standard）が提案する「.AI-rules」ファイルは、2025年に向けて複数のAIコーディングアシスタント（Cursor、Claude、Gemini、Copilotなど）のルールを一元管理する標準規格として注目されています。

- AIツールの統合標準化の動きは、Sakana AIのTreeQuestのように複数のLLMを連携させて単一モデルより30%以上の性能向上を実現する技術と同様に、開発効率の大幅な改善を目指しています。

- GitHubで公開されているARSプロジェクトは、AI支援コーディングの簡素化と標準化を促進するムーブメントの一環であり、TNG Technology ConsultingがDeepSeekモデルで実現した200%の処理速度向上のような技術革新と共鳴しています。

- 現状では各AIツール（.cursorrules、.claude.md、windsurf_rules.md、gemini.md、copilot_rules.yaml）ごとに異なるルールファイルを管理する非効率な状況を解消し、開発ワークフローを合理化することが目標とされています。

> **VentureBeat AI** (https://venturebeat.com/ai/sakana-ais-treequest-deploy-multi-model-teams-that-outperform-individual-llms-by-30/): 🆙 Sakana AI’s TreeQuest: Deploy multi-model teams that outperform individual LLMs by 30%
> Sakana AIが開発したTreeQuestは。複数のLLMを階層的に組み合わせたマルチモデルチームを構築し。単一モデルと比較して30%の性能向上を実現。
> **VentureBeat AI** (https://venturebeat.com/ai/holy-smokes-a-new-200-faster-deepseek-r1-0528-variant-appears-from-german-lab-tng-technology-consulting-gmbh/): 🆙 HOLY SMOKES! A new, 200% faster DeepSeek R1-0528 variant appears from German lab TNG Technology Consulting GmbH
> ドイツのTNG Technology Consulting GmbHが。DeepSeek R1-0528の処理速度を200%高速化した新バリアントを開発。従来モデルの3倍の推論性能を実現し。

**関連記事**: [2025年06月28日: Gemini標準機能で進化するAI小説執筆ワークフロー](https://zenn.dev/search?q=AI), [2025年06月28日: AIコーディングの精度を劇的に向上させる「Context7」とは](https://zenn.dev/search?q=Context7+AI), [2025年07月02日: AI（Gemini）を使って利用中Windowsソフトウェアの](https://zenn.dev/search?q=AI)

---

## 4. Gemini CLIとClaude Code性能比較、OpenAIは4.5ギガワット追加で複数AIエージェント協働に注力

- Gemini CLIとClaude Codeの比較検証が行われ、同一タスクでの両AIコーディングエージェントの性能や特性の違いが明らかにされています。Claude Codeは頻繁なアップデートが行われており、進化が続いています。

- AIコーディングエージェント市場は急速に発展しており、OpenAIが「Stargate AI」プロジェクトでOracleから4.5ギガワットの計算能力を追加レンタルするなど、大手企業による計算基盤の大規模拡張が進んでいます。

- 現在のAI開発トレンドとして、単一のコーディングエージェントの性能向上だけでなく、複数のAIエージェントを協働させる方法が次のブレイクスルーとして注目されており、開発効率の飛躍的向上が期待されています。

- Gemini CLIは比較的新しいツールながらも実用性を示しており、Claude Codeとの機能差や得意分野の違いを理解することで、開発者は目的に応じた最適なAIコーディングアシスタントを選択できるようになっています。

> **The Decoder** (https://the-decoder.com/openai-to-tap-4-5-gw-of-oracle-data-center-power-for-stargate-ai-project/): 🆙 OpenAI to tap 4.5 GW of Oracle data center power for Stargate AI project
> OpenAIが「Stargate」AIプロジェクト向けにOracleのデータセンターから4.5GW規模の電力供給を受ける契約を締結。GPT-5開発に向けた大規模コンピューティング基盤の構築を加速。
> **Zenn Ai General** (https://zenn.dev/carenet/articles/75be26456ca96b): [2025年7月4日] コーディングエージェントの協働が多分次のブレイクスルー (週刊AI)
> 複数のコーディングエージェントが連携して問題解決する協働型AIが2025年に主流化し、単体では解決困難な複雑なプログラミング課題を分散処理で克服する新パラダイム到来

**関連記事**: [2025年06月28日: Claude CodeとGemini CLIを対話させる mcp-gemini-cliの紹介](https://zenn.dev/search?q=CLI), [2025年06月28日: Gemini CLIを使いこなすためのツール活用ガイド](https://zenn.dev/search?q=CLI+%E3%83%84%E3%83%BC%E3%83%AB), [2025年06月28日: コラム｜Gemini CLIでブログを書いてみた感想と、そもそもCLIって何？](#note.com_20250628_aa7152aa)

---

## 5. DeepSeek R1続報：OpenAI価格80%引下げ誘発、コーディング性能さらに向上🆙

- DeepSeek R1は発表から約150日で、OpenAIの推論能力に匹敵する初の公開モデルとなり、$0.55/入力・$2.19/出力という破格の低価格設定で当時のSOTAモデルより90%以上安い価格を実現しました。

- DeepSeekの登場以降、OpenAIは自社フラッグシップモデルの価格を80%引き下げるなど、高性能推論モデルの価格は大幅に下落し、市場競争が激化しています。

- DeepSeekはリリース後も強化学習のスケーリングを継続し、特にコーディング分野で性能向上を実現していますが、消費者向けアプリのトラフィックは初期の急増後に減少傾向にあります。

- サードパーティによるDeepSeekモデルのホスティングは好調を維持しており、プロンプト分割などの技術革新と組み合わせることでLLMの推論能力をさらに向上させる可能性があります。

> **The Decoder** (https://the-decoder.com/ilya-sutskever-says-we-have-the-compute-we-have-the-team-and-we-know-what-to-do/): 🆙 Ilya Sutskever says, "We have the compute, we have the team, and we know what to do"
> OpenAIの共同創業者Sutskever、AGI実現に必要な3要素『計算能力』『チーム』『方法論』を既に保有と断言。次世代AIへの自信を示す発言が業界に波紋
> **Zenn Llm** (https://zenn.dev/maronn/articles/upgrade-llm-tracing-by-cognitive): 🆙 プロンプト分割によって、LLMの推論能力を引き上げる
> 複雑なタスクを小さなステップに分解するプロンプト分割技術により。GPT-4などのLLMは最大40%の精度向上を実現。特に数学問題や論理的推論で効果を発揮し。
> **Semianalysis** (https://semianalysis.com/2025/07/03/deepseek-debrief-128-days-later/): 🆙 DeepSeek Debrief: >128 Days Later
> DeepSeekのLLMが128日間の進化で。コンテキスト長8Kから128Kへ拡張。推論速度2倍向上。コード生成能力でHumanEvalで80%超えの精度を達成。

**関連記事**: [2025年07月03日: # 日本語翻訳

DeepSeek総括：128日以上が経過して](#semianalysis.com_20250703_7486016f), [2025年07月03日: # 驚愕！ドイツのTNG社から200%高速化した新DeepSeek R1-0528登場](#venturebeat.com_20250703_6dcea7ee), [2025年06月27日: # 日本語タイトル
モデルミニマリズム：企業に数百万ドルの節約をもたらす新AI戦略](#venturebeat.com_20250627_19b31fe7)

---

## 6. 【続報】Sakana AI、複数LLM連携技術「TreeQuest」で性能30%向上、企業の複雑タスク処理を効率化🆙

- Sakana AIが新たに開発したTreeQuestは、モンテカルロ木探索を活用して複数のLLMを連携させる推論時スケーリング技術で、単一モデルと比較して30%の性能向上を実現しています。

- この技術では複数のAIモデルがチームとして協働し、それぞれのモデルの強みを活かしながら複雑なタスクに対処することで、個々のLLMの限界を超える問題解決能力を提供します。

- TreeQuestは推論時に動的にモデルを組み合わせるアプローチを採用しており、従来の単一モデルや事前定義された連携方法と異なり、タスクに応じて最適なモデル連携パターンを自動的に構築します。

- この技術革新により、企業は複数のAIモデルを効率的に活用できるようになり、特に複雑な意思決定や創造的タスクにおいて大きな性能向上が期待できます。

> **VentureBeat AI** (https://venturebeat.com/ai/sakana-ais-treequest-deploy-multi-model-teams-that-outperform-individual-llms-by-30/): 🆙 Sakana AI’s TreeQuest: Deploy multi-model teams that outperform individual LLMs by 30%
> Sakana AIが開発したTreeQuestシステムは。複数のLLMを階層的に組織化し。単一モデルと比較して30%の性能向上を実現。特に複雑な推論タスクで威力を発揮し。

**関連記事**: [2025年07月03日: Sakana AI’s TreeQuest: Deploy multi-model teams that outperform individual LLMs by 30%](#venturebeat.com_20250703_d07b1ca3), [2025年06月27日: # 日本語タイトル
モデル・ミニマリズム：企業に数百万ドルの節約をもたらす新AI戦略](#venturebeat.com_20250627_19b31fe7), [2025年07月03日: # 驚愕！ドイツのTNG社から200%高速化した新DeepSeek R1-0528登場](#venturebeat.com_20250703_6dcea7ee)

---

## 7. DeepSeek R1新バージョン、TNG社の独自技術で処理速度200%向上の大幅進化🆙

- ドイツのTNG Technology Consulting GmbHが開発したDeepSeek R1-0528の新バリアントは、従来モデルと比較して処理速度が200%向上しており、AI言語モデルの実用性を大幅に高めています。

- この高速化はTNGが独自開発した「Assembly-of-Experts（AoE）」手法によって実現されており、重み付けテンソルを選択的に統合することでモデルの効率性を飛躍的に向上させています。

- DeepSeekモデルの高速化は、リアルタイム応用やエンタープライズ環境での実装において大きな意義を持ち、計算資源の制約がある状況でも高性能なAI活用を可能にしています。

> **VentureBeat AI** (https://venturebeat.com/ai/holy-smokes-a-new-200-faster-deepseek-r1-0528-variant-appears-from-german-lab-tng-technology-consulting-gmbh/): 🆙 HOLY SMOKES! A new, 200% faster DeepSeek R1-0528 variant appears from German lab TNG Technology Consulting GmbH
> ドイツのTNG Technology Consulting GmbHが。DeepSeek R1-0528の処理速度を200%高速化した新バリアントを開発。

**関連記事**: [2025年07月03日: # 驚愕！ドイツのTNG社から200%高速化した新DeepSeek R1-0528モデル登場](#venturebeat.com_20250703_6dcea7ee), [2025年07月03日: # DeepSeek振り返り：128日以上経過して](#semianalysis.com_20250703_7486016f), [2025年06月29日: # 日本語タイトル
研究者ら、「データの壁」を乗り越える手段を発見か](#the-decoder.com_20250629_68262fef)

---

## 8. 【続報】OpenAI「Stargate AI」計画、Oracle基盤から4.5ギガワット追加調達へ🆙

- OpenAIが「Stargate AI」プロジェクト向けに、Oracleの米国データセンターから追加で4.5ギガワットの計算能力を借り入れる計画を進めており、大規模なAI開発基盤の拡充を図っています。

- この大規模な電力供給契約は、OpenAIの次世代AIモデル開発に必要な計算リソースの確保を意味し、同社の野心的なAI開発戦略の重要な一歩となっています。

- 「Stargate」と名付けられたこのプロジェクトは、OpenAIがAI開発の競争において優位性を確保するための戦略的投資であり、大規模な計算インフラの確保が今後のAI開発の鍵となることを示しています。

> **The Decoder** (https://the-decoder.com/openai-to-tap-4-5-gw-of-oracle-data-center-power-for-stargate-ai-project/): 🆙 OpenAI to tap 4.5 GW of Oracle data center power for Stargate AI project
> OpenAIとOracleが提携し。Stargate AIプロジェクト向けに4.5GW規模の電力供給契約を締結。データセンター拡張による大規模AI計算基盤構築で。

**関連記事**: [2025年07月03日: OpenAI to tap 4.5 GW of Oracle data center power for Stargate AI project](#the-decoder.com_20250703_bd1634d3), [2025年06月29日: # 翻訳

OpenAIが開発者に深層研究エージェントの構築方法を指導](#the-decoder.com_20250629_bcb24363), [2025年06月28日: # 日本語タイトル
メタ、OpenAIからさらに4人の研究者を採用か](https://techcrunch.com/search/techcrunch.com_20250628_4152a2f8)

---

## 9. Claude CodeのAIClaude

- Claude Codeが頻繁にアップデートされる中、複数のコーディングエージェントを協働させる手法が注目を集めており、特にHooksのリリース以降、終了時に自動的に他のエージェントを呼び出してレビューや追加処理を行わせる活用法が広がっています。

- Claude Codeが自己参照による無限ループを避けつつ多段階処理を実現するために、複数のエージェントを連携させる方法が効果的なノウハウとして共有されており、開発プロセスの効率化に貢献しています。

- 現状のフロンティアモデル間では機能や特性の差異が少ないものの、o3とWeb検索を併用する手法も紹介されており、今後は各AIが得意分野を持つようになることで、より専門的なタスクに対応できる協働体制が構築される可能性があります。

> **Zenn Ai General** (https://zenn.dev/carenet/articles/75be26456ca96b): [2025年7月4日] コーディングエージェントの協働が多分次のブレイクスルー (週刊AI)
> 複数のコーディングエージェントが連携する新パラダイム。GitHub CopilotやAmazon Q Codeのような単体AIから。Claude+GPT-4のチーム開発体制へ移行し。

**関連記事**: [2025年07月03日: 🆙 Claude Codeに10万文字規模のSF小説「Ω分岐の書庫」を書かせてみた](https://zenn.dev/search?q=%CE%A9%E5%88%86%E5%B2%90%E3%81%AE%E6%9B%B8%E5%BA%A), [2025年07月03日: 🆙 神がかり的AIがきた！](#note.com_20250703_af058f38), [2025年07月03日: Claude Code がインストールしていないツールを使いこなしている！？](https://zenn.dev/search?q=%E3%83%84%E3%83%BC%E3%83%AB)

---

## 10. OpenAI共同創業者の新会社SSI、続報：Sutskever CEOが超知能AI開発の3要素を確保と自信🆙

- OpenAIの共同創業者であるIlya Sutskeverが新たに立ち上げたSafe Superintelligence Inc.（SSI）のCEOに就任し、「必要な計算能力、チーム、そして何をすべきかを知っている」と自信を示しています。

- Sutskeverは人工知能の安全性研究の第一人者として知られており、SSIは超知能AIの安全な開発を目指す新興企業として注目を集めています。

- OpenAIからの独立後、Sutskeverは計算資源の確保、専門家チームの編成、明確なビジョンの3要素を揃え、AIの安全性と能力向上の両立を目指す姿勢を明確にしています。

> **The Decoder** (https://the-decoder.com/ilya-sutskever-says-we-have-the-compute-we-have-the-team-and-we-know-what-to-do/): 🆙 Ilya Sutskever says, "We have the compute, we have the team, and we know what to do"
> OpenAIの共同創業者Sutskever、AGI実現に必要な3要素『計算能力、チーム、方法論』を既に保有と断言。次世代AIへの自信を示唆

**関連記事**: [2025年07月03日: # イリヤ・サツケバー「計算資源、チーム、そして進むべき道がある](#the-decoder.com_20250703_8c8c02fa), [2025年06月27日: # 日本語翻訳

メタCTO、トップAI幹部への高額オファーを認める](#the-decoder.com_20250627_c8c315dc), [2025年06月28日: # 日本語翻訳

「OpenAI、主要研究者4名をMetaに奪われる](#wired.com_20250628_ed221428)

---

## Lawrence's Insights

*※ここにLawrenceさんの手入力コメントを追加してください*

---
