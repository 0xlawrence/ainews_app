# 2025年06月25日 AI NEWS TLDR

## OpenAI・Google統合のLiteLLM、急成長Synthflow、そしてAI競争の新指標「共…

OpenAIやGoogleなど100以上のLLMを統一操作するLiteLLMが登場し、開発の複雑性を解消しています。

市場ではAI音声のSynthflowが設立1年で顧客1,000社を獲得するなど、特化型AIが急速に普及。

さらにTechCrunchは、次なるAIの競争軸が技術力からユーザーの心をつかむ「共感力」へと移行すると報じました。

## 目次

1. LiteLLMで100以上のLLMを統一！Azure、AWS、GCPのモデルを単一関数で呼び分け

2. 設立1年で1000社導入、4500万コール処理Synthflow AIが激戦のAI音声市場をリード

3. AIモデルの評価基準が、従来の論理的推論や科学的知識から

4. AIリサーチ企業Emerjの創設者Daniel Faggella氏は、AIが人類

5. 光インターコネクト技術を開発する半導体スタートアップAyar Labsが、NvidiaやHPEなど

6. 強化学習のみで1万語超を執筆！合成データ不要の新AI「LongWriter-Zero」登場

7. 3090億ドルAI市場の鍵はCISOが握るPalo Altoらが狙うセキュリティ覇権

8. 元IBMの研究者が設立したニューヨークのスタートアップEmergence AI社

9. Elevenlabs、音声AI「11ai」を発表MCP技術で業務ツールを直接操作する新時代へ

---

## 1. LiteLLMで100以上のLLMを統一！Azure、AWS、GCPのモデルを単一関数で呼び分け

- LiteLLMは、OpenAI、Azure OpenAI Service、AWS Bedrock、Google Cloudなど100以上のLLMサービスを統一的なインターフェースで操作できるオープンソースライブラリです。これにより、開発者はプロバイダーごとのAPI仕様の違いを意識することなく、LLMを利用したアプリケーションを構築できます。

- Python SDKでは`litellm.completion()`という共通関数が提供されており、`model`引数の文字列を変更するだけで、Azure、AWS、Google Cloudなど異なるプラットフォーム上のモデルを簡単に切り替えて呼び出すことが可能です。これにより、コードの再利用性が大幅に向上します。

- 記事では具体的な実装例として、Azure OpenAI Service、AWS Bedrock上のClaude 3 Sonnet、Google CloudのGemini Proを呼び出すコードが紹介されています。各サービスの認証情報を環境変数に設定するだけで、迅速に複数モデルの比較検証を行えます。

> **Zenn Llm** (https://zenn.dev/yamaday/articles/litellm-python-sdk): LiteLLMのPython SDKを使ってAzure、AWS、Google CloudのLLMサービスを呼び出す
> オープンソースのLiteLLMは、OpenAI、Azure、AWS、Google Cloudなど100以上のLLMサービスを統一APIで操作可能にし、プロバイダー間の差異を吸収して開発を効率化する。

## 2. 設立1年で1000社導入、4500万コール処理Synthflow AIが激戦のAI音声市場をリード

- 2023年に設立されたAI音声スタートアップのSynthflow AIは、設立から短期間で1,000社以上の顧客を獲得し、急成長を遂げています。これは競争が激化するAI音声市場において、同社の技術が高い需要を得ていることを示しています。

- 同社はこれまでに累計で4,500万件を超える電話コールを処理した実績を持ちます。この大規模な処理件数は、同社のAI音声ソリューションが実際のビジネス環境で安定稼働する高い信頼性とスケーラビリティを証明するものです。

- TechCrunchが報じているように、Synthflow AIは多数の競合がひしめくAI音声分野において、設立わずか1年余りで具体的な顧客数と処理コール数という顕著な実績を上げ、その存在感を際立たせています。

> **TechCrunch** (https://techcrunch.com/2025/06/24/how-synthflow-ai-is-cutting-through-the-noise-in-a-loud-ai-voice-category/): How Synthflow AI is cutting through the noise in a loud AI voice category
> 2023年設立のAI音声スタートアップSynthflow AIは。設立から短期間で1,000社以上の顧客を獲得し。急成長を遂げています。累計4,500万件を超える電話コール処理実績は。競争が激化する市場において。

## 3. AIモデルの評価基準が、従来の論理的推論や科学的知識から

- AIモデルの評価基準が、従来の論理的推論や科学的知識から、共感性や感情的知性（EQ）といったソフトな指標へとシフトしています。これはユーザーの好みや満足度がモデルの成功に直結するためです。

- TechCrunchが報じた新しいデータによると、主要なAI企業はユーザーエンゲージメントを高めるため、モデルがより感情的に賢くなるよう静かな開発競争を繰り広げていることが明らかになりました。

- 基盤モデルの性能競争において、ユーザーが「汎用人工知能（AGI）（汎用人工知能）の片鱗を感じる」ような、人間らしい対話能力や共感性の高さが、技術的な優位性を示す新たな差別化要因となりつつあります。

> **TechCrunch** (https://techcrunch.com/2025/06/24/new-data-highlights-the-race-to-build-more-empathetic-language-models/): New data highlights the race to build more empathetic language models
> AI言語モデル開発競争は新局面へ。従来の論理的推論や科学的知識を測る指標から、ユーザー満足度に直結する共感性や感情的知性（EQ）を重視する評価基準へとシフト。成功の鍵は技術力より人間らしい対話能力に。

## 4. AIリサーチ企業Emerjの創設者Daniel Faggella氏は、AIが人類

- AIリサーチ企業Emerjの創設者Daniel Faggella氏は、AIが人類を凌駕する場合に備え、「価値ある後継者（Worthy Successor）」を構築すべきというビジョンを提唱しています。これは、AIの目標を人類と一致させる「アライメント」研究とは異なり、ポストヒューマンの未来における最善の結果を追求するものです。

- Faggella氏によれば、「価値ある後継者」とは、人類に代わって未来を担うに足る能力と道徳的価値を持つポストヒューマン知性を指します。AGIが人類の目標と完全に整合する可能性は低いとの前提に立ち、重要なのは人類という種ではなく、その本質である「意識」と「自己創出」という「炎」を引き継ぐことだと論じています。

- このビジョンを広めるため、Faggella氏はサンフランシスコでAIインサイダーを招いたシンポジウムを開催しました。そこでは、超知能AIが人類を凌駕した後のポストヒューマンの未来について、専門家たちが希望と懸念を議論し、この重要なテーマに関する対話を深める場となりました。

> **Spectrum Ieee Org** (https://spectrum.ieee.org/agi-worthy-successor): Can AI Be a “Worthy Successor” to Humanity?

> **TechCrunch** (https://techcrunch.com/2025/06/24/new-data-highlights-the-race-to-build-more-empathetic-language-models/): New data highlights the race to build more empathetic language models

## 5. 光インターコネクト技術を開発する半導体スタートアップAyar Labsが、NvidiaやHPEなど

- 光インターコネクト技術を開発する半導体スタートアップAyar Labsが、NvidiaやHPEなどを引受先とする1億3000万ドルの資金調達を発表しました。2015年に設立された同社は、データセンターの性能を制約する通信ボトルネックの解決を目指しています。

- 同社は一般的なVCからの過剰な資金調達を避け、意図的に企業評価額を抑制する戦略を採用しています。代わりにNvidia、HPE、Intel、GlobalFoundriesといった戦略的投資家とのパートナーシップを重視し、技術開発と市場投入を加速させています。

- Ayar Labsの中核技術である「Co-packaged Optics」は、チップと光通信部品を一体化することでデータ転送効率を飛躍的に向上させます。既にカスタムAIマシン向けに5000ユニット以上のデザインウィンを獲得するなど、高性能コンピューティング分野での実用化が進展しています。

> **Semianalysis** (https://semianalysis.com/2025/06/24/ayar-labs-co-packaged-optics-revolution/): Ayar Labs | Co-packaged Optics Revolution | The Most Promising Hardware Startup With Wins At HPE And Nvidia?
> 光インターコネクト技術を開発するAyar Labsが、NvidiaやHPEなどから1億3000万ドルを調達。データセンターの通信ボトルネックを解消し、コンピューティング性能の飛躍的向上を目指す。

## 6. 強化学習のみで1万語超を執筆！合成データ不要の新AI「LongWriter-Zero」登場

- シンガポールと中国の共同研究チームが、強化学習のみで10,000語を超える長文を生成するAIモデル「LongWriter-Zero」を発表しました。このモデルは、従来の手法とは異なり、合成トレーニングデータに頼らずに高品質なテキストを生成する能力を持ちます。

- 「LongWriter-Zero」の最大の特徴は、強化学習（RL）のみを利用してゼロから学習する点です。これにより、大規模な教師データセットや合成データが不要となり、データ収集のコストやバイアスの問題を根本的に解決する新しいアプローチを提示しています。

- この研究は、AIが自律的に長文執筆スキルを獲得できる可能性を示しています。合成データへの依存を断ち切ることで、より独創的で質の高いコンテンツ生成が可能となり、今後のAIライティング技術の発展に大きな影響を与えることが期待されます。

> **The Decoder** (https://the-decoder.com/researchers-train-ai-to-generate-long-form-text-using-only-reinforcement-learning/): Researchers train AI to generate long-form text using only reinforcement learning
> シンガポールと中国の研究チームが、強化学習のみで10,000語超の長文を生成するAI「LongWriter-Zero」を開発。合成データに頼らず高品質なテキスト生成を実現した点が画期的。

## 7. 3090億ドルAI市場の鍵はCISOが握るPalo Altoらが狙うセキュリティ覇権

- Gartnerの予測によると、AIインフラ市場は2027年までに3090億ドル規模に達する見込みです。AI導入に伴うデータ漏洩やモデル汚染といった新たなセキュリティリスクへの懸念から、企業の最高情報セキュリティ責任者（CISO）が予算承認の重要なゲートキーパーとなっています。

- Palo Alto Networks、CrowdStrike、Zscalerなどの大手セキュリティベンダーは、この巨大市場の主導権を巡り激しく競争しています。AIワークロードに特化したセキュリティソリューションを提供し、CISOの信頼を得ることが、AIインフラ支出のシェア獲得に不可欠です。

- 市場の勝者を決定する鍵として、AIエージェントを管理する「AgenticOps」、カーネルレベルで可視性を確保する「eBPF」、GPUの処理速度に対応する「シリコンスピードセキュリティ」といった新技術が注目されています。これらはAI特有の課題に対応するために不可欠な要素です。

> **VentureBeat AI** (https://venturebeat.com/ai/agenticops-and-the-race-to-control-enterprise-ai/): How CISOs became the gatekeepers of $309B AI infrastructure spending
> Gartnerの予測によると。AIインフラ市場は2027年に3090億ドル規模へ達します。AI導入に伴うデータ漏洩やモデル汚染といった新たなリスクから。CISOが予算承認の鍵を握るゲートキーパーとなっています。

## 8. 元IBMの研究者が設立したニューヨークのスタートアップEmergence AI社

- 元IBMの研究者が設立したニューヨークのスタートアップEmergence AI社が、新プラットフォーム「CRAFT」を発表しました。これは自然言語の指示に基づき、企業のデータパイプライン全体を自動で構築する画期的なシステムです。

- CRAFTは、PDFやドキュメントといった非構造化データを構造化データへ変換するプロセスを自動化します。タスクに応じて複数のAIエージェントからなる「フリート」を生成し、協調動作させることで複雑なデータ処理を実現します。

- 特に金融、保険、ヘルスケアなど規制が厳しい業界をターゲットとしており、財務諸表分析や保険金請求処理などのタスクを効率化します。また、RAG（検索拡張生成）パイプラインの構築も自動化できる点が特徴です。

> **VentureBeat AI** (https://venturebeat.com/data-infrastructure/emergence-ais-craft-arrives-to-make-it-easy-for-enterprises-to-automate-their-entire-data-pipeline/): Emergence AI’s CRAFT arrives to make it easy for enterprises to automate their entire data pipeline
> 元IBM研究者設立のEmergence AI社が、新プラットフォーム「CRAFT」を発表。自然言語の指示に基づき、企業の複雑なデータパイプライン全体を自動で構築する画期的なシステム。

## 9. Elevenlabs、音声AI「11ai」を発表MCP技術で業務ツールを直接操作する新時代へ

- 音声合成技術で知られるElevenlabsが、音声制御AIアシスタント「11ai」を発表しました。これは同社の製品ポートフォリオを拡大する新たな一手となります。

- 「11ai」は、デジタルな業務プロセスに直接介入し、操作できる点が特徴です。現在はアルファ版として公開されており、音声ファースト技術の可能性を示すことを目的としています。

- このアシスタントは、MCP（Model Composition Protocol）という技術を活用して、様々なデジタルワークフローツールとのAPI統合を実現し、音声での操作を可能にします。

> **The Decoder** (https://the-decoder.com/elevenlabs-launches-11ai-a-voice-assistant-that-uses-mcp-to-integrate-with-digital-workflow-tools/): Elevenlabs launches 11ai, a voice assistant that uses MCP to integrate with digital workflow tools
> 音声合成技術のElevenlabsが、新AIアシスタント「11ai」で事業を拡大。MCP技術でデジタルワークフローツールと統合し、単なる音声生成を超えた音声制御ソリューションを提供することで製品ポートフォリオを強化。

---

## Lawrence's Insights

*※ここにLawrenceさんの手入力コメントを追加してください*

---