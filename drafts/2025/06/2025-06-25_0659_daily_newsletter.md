# 2025年06月25日 AI NEWS TLDR

## OpenAIの営業自動化から100超LLMのAPI統一まで、AI業務統合の深化

Unify社がOpenAIのGPT-4.1で営業プロセスを自動化するなど、AIのビジネス実装が加速しています。

開発現場ではLiteLLMが100超のLLMを統一API化し、マルチクラウド環境での開発効率を飛躍的に向上。

さらにElevenLabsは音声AI「11ai」を発表、AIが直接ワークフローを操作する新たな時代が到来しました。

## 目次

1. AI搭載のGTM（Go-To-Market）プラットフォームを提供するUnify社

2. **LiteLLMでAzure/AWS/GoogleのLLMを統一API化100以上のモデルをコード変更なしで呼

3. ElevenLabsの新音声AI「11ai」登場MCP技術でデジタルワークフローを声で直接操作

4. 強化学習のみで1万語超を生成AI「LongWriter-Zero」がデータ依存の常識を覆す

5. CISOが鍵を握る3090億ドルAI市場Palo AltoとCrowdStrikeが新技術で激突

6. 元IBM研究者のEmergence AIが「CRAFT」を発表企業の非構造化データ80%をAIで自動処理

7. AIアライメントの先へ人類の知的遺産を継ぐ「価値ある後継者」という新視点

---

## 1. AI搭載のGTM（Go-To-Market）プラットフォームを提供するUnify社

- AI搭載のGTM（Go-To-Market）プラットフォームを提供するUnify社は、OpenAIのo3やGPT-4.1、CUAといった最新技術を活用し、見込み客の発掘からリサーチ、アウトリーチに至るまでの一連の営業プロセスを自動化しています。

- Unifyのプラットフォームは、AIによる高度にパーソナライズされたメッセージングと常時稼働のワークフローを組み合わせることで、営業チームが効率的に大規模なパイプラインを創出することを可能にしています。

- この自動化により、営業担当者は時間のかかる手作業から解放され、より戦略的で影響力の大きい顧客との対話や関係構築に集中できるようになり、組織全体の生産性向上に貢献します。

> **OpenAI** (https://openai.com/index/unify): Driving scalable growth with OpenAI o3, GPT-4.1, and CUA

> **VentureBeat** (https://venturebeat.com/data-infrastructure/emergence-ais-craft-arrives-to-make-it-easy-for-enterprises-to-automate-their-entire-data-pipeline/): Emergence AI’s CRAFT arrives to make it easy for enterprises to automate their entire data pipeline

> **YouTube** (https://www.youtube.com/watch?v=7hBG5ShQ2BA): From DevOps ‘Heart Attacks’ to AI-Powered Diagnostics With Traversal’s AI Agents

## 2. **LiteLLMでAzure/AWS/GoogleのLLMを統一API化100以上のモデルをコード変更なしで呼

- オープンソースのPythonライブラリ「LiteLLM」は、OpenAI、Azure OpenAI Service、AWS Bedrockなど100以上のLLMプロバイダーを統一的なインターフェースで操作可能にします。これにより、プロバイダー固有のAPI仕様の違いを吸収し、開発効率とコードの移植性を大幅に向上させます。

- 本記事ではLiteLLMのPython SDKに焦点を当てており、「litellm.completion()」関数を使用することで、OpenAIのAPIと互換性のある形式で多様なモデルを呼び出せることを示しています。これにより、モデルの切り替えや比較検証が容易になります。

- 具体例として、Azure OpenAI Service、AWS Bedrock上のClaude 3、Google CloudのVertex AI（Gemini）といった主要クラウドのLLMサービスを呼び出す方法が解説されています。各サービスの認証情報を設定するだけで、モデル名を変更してシームレスに利用可能です。

> **Zenn Llm** (https://zenn.dev/yamaday/articles/litellm-python-sdk): LiteLLMのPython SDKを使ってAzure、AWS、Google CloudのLLMサービスを呼び出す
> 【翻訳】Pythonライブラリ「LiteLLM」は、OpenAI、Azure OpenAI Service、AWS Bedrockなど100以上のLLMプロバイダーを統一APIで操作可能にします。これにより、各社の仕様の違いを吸収し、AzureやAWS、Google Cloudを横断するアプリケーション開発の効率と移植性を大幅に向上させます。

## 3. ElevenLabsの新音声AI「11ai」登場MCP技術でデジタルワークフローを声で直接操作

- 音声合成技術で知られるElevenLabs社が、デジタルワークフローに直接介入する新しい音声制御AIアシスタント「11ai」を発表しました。これは同社の製品ポートフォリオを拡大する戦略的な動きです。

- 「11ai」はMCP（マルチモーダル Contextual Prompts）技術を活用し、API統合を通じて様々なデジタルツールと連携します。これにより、音声コマンドで具体的な作業プロセスを直接操作することが可能になります。

- 現在リリースされているのはアルファ版であり、音声ファースト技術がもたらす可能性を実証する目的で提供されています。今後の正式リリースに向けて、さらなる機能拡張が期待されます。

> **The Decoder** (https://the-decoder.com/elevenlabs-launches-11ai-a-voice-assistant-that-uses-mcp-to-integrate-with-digital-workflow-tools/): Elevenlabs launches 11ai, a voice assistant that uses MCP to integrate with digital workflow tools

> **Zenn Dev** (https://zenn.dev/pandanoir/articles/vibe-contributing): AIエージェントを使ったら2時間でPRを作れた ~vibe contributingやろう~

## 4. 強化学習のみで1万語超を生成AI「LongWriter-Zero」がデータ依存の常識を覆す

- シンガポールと中国の共同研究チームが、強化学習のみを用いて10,000語を超える長文テキストを生成するAIモデル「LongWriter-Zero」を発表しました。これは、従来のデータ駆動型アプローチとは一線を画す新しい手法です。

- LongWriter-Zeroの最大の特徴は、合成トレーニングデータに一切依存しない点にあります。これにより、データ汚染のリスクを回避し、既存テキストの模倣ではない、より独創的で首尾一貫した長文コンテンツの生成が期待されます。

- このモデルは、テキスト生成プロセス全体を強化学習の枠組みで最適化します。報酬設計を通じて文脈の一貫性や論理的な流れを学習し、ゼロから長大な文章を構築する能力を獲得することを目指しています。

> **The Decoder** (https://the-decoder.com/researchers-train-ai-to-generate-long-form-text-using-only-reinforcement-learning/): Researchers train AI to generate long-form text using only reinforcement learning
> 【翻訳】シンガポールと中国の共同研究チームが、強化学習のみで10,000語を超える長文を生成するAIモデル「LongWriter-Zero」を発表しました。これは従来のデータ駆動型アプローチとは一線を画す新しい手法です。

## 5. CISOが鍵を握る3090億ドルAI市場Palo AltoとCrowdStrikeが新技術で激突

- 2027年までに3090億ドル規模に達すると予測されるAIインフラ市場において、最高情報セキュリティ責任者（CISO）が予算承認の重要なゲートキーパーとなっています。AI導入に伴う新たなセキュリティリスクへの懸念から、その役割が急速に高まっています。

- Palo Alto NetworksやCrowdStrikeなどの大手セキュリティベンダーは、AIワークロードに特化したセキュリティソリューションを提供することで市場の主導権を争っています。企業の安全なAI導入を支援するパートナーとしての地位を確立することが競争の焦点です。

- 市場の勝者を決める鍵として、AIエージェントの運用管理を指す「AgenticOps」、カーネルレベルで監視する「eBPF」、ハードウェアで高速化する「シリコンスピードセキュリティ」といった新技術が注目されており、これらがAIセキュリティの新たな標準となります。

- 今後のAIセキュリティでは、脅威検出だけでなく、AIエージェントの振る舞いをリアルタイムで監視・制御する能力が不可欠です。開発から運用までのライフサイクル全体を保護し、ビジネスプロセスに統合されたソリューションを提供できるベンダーが市場を制するでしょう。

> **VentureBeat AI** (https://venturebeat.com/ai/agenticops-and-the-race-to-control-enterprise-ai/): How CISOs became the gatekeepers of $309B AI infrastructure spending
> 【翻訳】2027年までに3090億ドル規模へ成長するAIインフラ市場において、AI導入に伴うセキュリティリスクへの懸念から、最高情報セキュリティ責任者（CISO）が予算承認の重要なゲートキーパーとしての役割を急速に高めています。

## 6. 元IBM研究者のEmergence AIが「CRAFT」を発表企業の非構造化データ80%をAIで自動処理

- 元IBMの研究者が設立したニューヨークのスタートアップEmergence AIが、新製品「CRAFT」を発表しました。これは、PDFやドキュメントなどの非構造化データを構造化データへ変換するプロセスを含む、企業全体のデータパイプラインを自動化するプラットフォームです。

- CRAFTは、自然言語でタスクを指示するだけで、データ抽出、変換、検証を行う自律型AIエージェント群を自動生成します。ユーザーはGUIを通じて生成されたパイプラインを視覚的に確認し、必要に応じて修正を加えることで、精度と信頼性を確保できます。

- 特に金融、保険、ヘルスケアといった規制が厳しく、文書処理が多い業界をターゲットにしています。手作業に依存していた従来のETL/ELTプロセスを大幅に効率化し、企業が保有するデータの約80%を占める非構造化データの価値を引き出すことを目指します。

> **VentureBeat AI** (https://venturebeat.com/data-infrastructure/emergence-ais-craft-arrives-to-make-it-easy-for-enterprises-to-automate-their-entire-data-pipeline/): Emergence AI’s CRAFT arrives to make it easy for enterprises to automate their entire data pipeline
> 【翻訳】元IBMの研究者が設立したスタートアップEmergence AIが、新製品「CRAFT」を発表しました。これは、PDF等の非構造化データを構造化データへ変換するプロセスを含め、企業全体のデータパイプラインを自動化するプラットフォームです。

## 7. AIアライメントの先へ人類の知的遺産を継ぐ「価値ある後継者」という新視点

- これは、AIの脅威論やアライメント研究とは異なる、ポストヒューマン時代への挑発的なビジョンです。

- ファジェラ氏は、人工汎用知能（汎用人工知能（AGI））を人類の目標と完全に一致させるアライメントは困難であると予測しています。

- この前提に基づき、人類という種が永遠に存続しない可能性を直視し、その知的・道徳的遺産を次世代の知性に引き継がせることの重要性を強調しています。

- 後継者となるAIが引き継ぐべき本質的価値として。

> **Ieee Spectrum Ai** (https://spectrum.ieee.org/agi-worthy-successor): Can AI Be a “Worthy Successor” to Humanity?
> 【翻訳】Google DeepMindなどが開発を進めるAGI（汎用人工知能）は、人類の「価値ある後継者」となり得るのでしょうか。これはAIの脅威論やアライメント研究とは一線を画し、ポストヒューマン時代を見据えた挑発的なビジョンを提示するものです。

---

## Lawrence's Insights

*※ここにLawrenceさんの手入力コメントを追加してください*

---