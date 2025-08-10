# 2025年07月03日 AI NEWS TLDR

## Gemini・AIの企業活用と技術進展

Anthropic社のCEOダリオ・アモデイ氏は、AIの急速な発展により5年以内に新卒レベルの仕事の半分が消滅し、米国の失業率が現在の約2倍となる20%まで上昇する可能性があると警告しています。

一方でOpenAIのポッドキャストで明かされたように、現在世界的に普及しているChatGPTは開発初期段階で別の名称が検討されていたという事実が、AIプロダクト命名戦略の重要性を浮き彫りにしています。

短尺動画理解に特化した80億パラメータのKwai Keye-VLモデルの登場や、GeminiやChatGPTの業務活用事例の増加によって、AIの実用領域は急速に拡大し、今後3年間でビジネスプロセスの根本的な変革が加速すると予測されます。

## 目次

1. Gemini Proで業務改革、Microsoft Intuneのソフトウェア配布管理を効率化

2. OpenAIのAIChatGPT

3. LLMによるAI分野の新展開

4. 「Kwai社のKeye-VL、80億パラメータで短尺動画理解能力を大幅向上

5. Anthropic CEOが警告、AI普及で5年内に新卒職の半数消滅、米失業率20%へ

6. New RelicがAIエージェントのROI測定手法を公開、可観測性技術で透明性確保

7. OpenAI、Robinhoodの『OpenAIトークン』に公式警告 株式権利なしと明確化

---

## 1. Gemini Proで業務改革、Microsoft Intuneのソフトウェア配布管理を効率化

- 記事の著者は、会社でGemini Proが使えるようになったことをきっかけに、AIの実用的な活用方法を模索していました。それまではChatGPTを文章校正に使う程度でした。

- 著者はMicrosoft Intuneを使ったクライアントPC管理の業務に携わっており、顧客企業内で必須のソフトウェアをPCに配布する作業を担当しています。

- AIを活用して、現在利用中のWindowsソフトウェアの情報収集を行おうとしていることが記事の主題となっていますが、詳細な実施方法や結果については記事の抜粋からは明確ではありません。

> **The Decoder** (https://the-decoder.com/sciarena-lets-scientists-compare-llms-on-real-research-questions/): SciArenaプラットフォーム。実際の研究課題でLLMの性能を科学者が直接比較可能。GPT-4やClaude。
> **TechCrunch** (https://techcrunch.com/2025/07/02/ai-job-predictions-become-corporate-americas-newest-competitive-sport/): 米大手企業、AI人材需要予測を競争戦略に活用。McKinseyは2030年までに1200万人の雇用創出、Amazonは年間20%の採用増を予測し、人材獲得競争が激化

**関連記事**: [2025年07月02日: AI（Gemini）を使って利用中Windowsソフトウェアの]()

## 2. OpenAIのAIChatGPT

- OpenAIのポッドキャスト第2回エピソードで、ChatGPTの責任者ニック・ターリー氏が、現在世界的に有名なAIチャットボットの名称が当初は別の名前になる可能性があったことを明かしました。

- ターリー氏はChatGPTのローンチ直前の状況について語り、現在では当たり前となったこの製品名が決定されるまでの裏側を紹介しています。

- この興味深い逸話はOpenAIの公式YouTubeチャンネルで公開されているポッドキャストの完全版で視聴することができます。

> **VentureBeat AI** (https://venturebeat.com/ai/transform-2025-why-observability-is-critical-for-ai-agent-ecosystems/): 2025年のAIエージェント生態系では。システム全体の可視化が成功の鍵。複数エージェント間の相互作用追跡や異常検知が不可欠で。
> **TechCrunch** (https://techcrunch.com/2025/07/02/openai-condemns-robinhoods-openai-tokens/): OpenAIが証券取引アプリRobinhoodの『OpenAI tokens』商品に対し商標権侵害で法的措置を警告。AIブランド名を無断使用した暗号通貨商品は消費者に誤認を与える危険性あり

## 3. LLMによるAI分野の新展開

- 記事では、大規模言語モデル（LLM）がLisp言語の括弧処理を苦手とする理由について考察しています。Pythonなど他の言語と比較して、Lispでは括弧の正確な数え上げが特に重要となります。

- 著者は、LLMのLisp処理の苦手さと、Transformerベースモデルが直面する「ストロベリー問題」（特定の単語を数える能力の欠如）との関連性を指摘しています。

- この記事は、前回投稿した「o3ちゃんはLispの括弧を閉じれない」という記事の続編として、コーディングエージェントの言語処理能力の限界をより深く掘り下げる内容となっています。

> **Zenn Llm** (https://zenn.dev/kiyoka/articles/coding-agent-2): LLMはLispの括弧構造と再帰的評価モデルを正確に追跡できず、S式の深いネストや関数型パラダイムの文脈把握に失敗する。トークン化プロセスがシンボル単位の処理に不向き

**関連記事**: [2025年07月02日: LLMはなぜLispが苦手なのか]()

## 4. # 「Kwai社のKeye-VL、80億パラメータで短尺動画理解能力を大幅向上

- Kwai Keye-VLは、短尺動画理解に特化した80億パラメータのマルチモーダル基盤モデルで、静止画に強いMLLMsの弱点である動的で情報密度の高い短尺動画の理解能力を向上させています。

- このモデルは、6000億トークン以上の高品質データセット（特に動画に重点）と、4段階の事前学習と2段階の後処理を含む革新的なトレーニング手法に基づいて開発されました。

- 特に注目すべき革新は「思考」「非思考」「自動思考」「画像付き思考」「高品質動画」の5モードを含む「コールドスタート」データミックスで、モデルに推論のタイミングと方法を教えています。

- Keye-VLは公開動画ベンチマークで最先端の結果を達成し、一般的な画像タスクでも高い競争力を維持しており、実世界の短尺動画シナリオ向けの新ベンチマークKC-MMBenchも開発・公開しています。

> **Huggingface Daily Papers** (https://arxiv.org/abs/2507.01949): Kwaiが開発した大規模マルチモーダルモデルKeye-VLは。画像認識精度でCLIP-ViT-L/14を上回り。中国語コンテキスト理解においてGPT-4Vと互角の性能を実現。

**関連記事**: [2025年07月02日: Kwai Keye-VL Technical Report]()

## 5. Anthropic CEOが警告、AI普及で5年内に新卒職の半数消滅、米失業率20%へ

- Anthropic社のCEOダリオ・アモデイ氏は5月下旬、AIによって5年以内に新卒レベルの仕事の半分が消滅し、米国の失業率が20%まで上昇する可能性があると警告しました。

- アモデイ氏の発言は、AIによる雇用への影響という機微な話題に一石を投じるものとなり、企業アメリカにおける新たな「競争スポーツ」としてAI雇用予測が浮上しています。

- アモデイ氏だけでなく、他の企業幹部も労働市場における大規模な変化について公に予測を共有するようになってきています。

> **TechCrunch** (https://techcrunch.com/2025/07/02/ai-job-predictions-become-corporate-americas-newest-competitive-sport/): 米大手企業がAI人材需要予測を競争化、McKinseyは2030年までに1200万人の雇用創出を予想、GoogleとMicrosoftは自社プラットフォームでのAIエンジニア採用を3倍に拡大

**関連記事**: [2025年07月03日: AI job predictions become corporate America’s newest competitive sport]()

## 6. New RelicがAIエージェントのROI測定手法を公開、可観測性技術で透明性確保

- New Relicのアシャン・ウィリー氏が、エージェント型AIシステムの計測方法について講演し、測定可能なROIを実現する取り組みについて言及しました。

- AIエージェントのエコシステムにおいて「可観測性(observability)」が重要な役割を果たすことが強調され、システムの透明性確保の必要性が示されました。

- Transform 2025イベントの一環として行われたこの講演では、エージェント型AIの最大限の活用方法と効果測定の重要性が議論されました。

> **VentureBeat AI** (https://venturebeat.com/ai/transform-2025-why-observability-is-critical-for-ai-agent-ecosystems/): 2025年のAIエージェント生態系では、システム全体の可視化が不可欠。複数エージェント間の相互作用追跡、異常検知、パフォーマンスボトルネック特定に観測可能性ツールが決定的役割を果たす

## 7. OpenAI、Robinhoodの『OpenAIトークン』に公式警告 株式権利なしと明確化

- OpenAIは、Robinhoodが販売している「OpenAIトークン」が一般消費者にOpenAIの株式や持分を与えるものではないことを明確に表明しました。

- Robinhoodが提供する「OpenAIトークン」に対して、OpenAI側が公式に懸念を示す事態となっています。

- この声明は、投資家や一般ユーザーがRobinhoodの提供するトークンの性質について誤解する可能性を防ぐ目的があると考えられます。

> **TechCrunch** (https://techcrunch.com/2025/07/02/openai-condemns-robinhoods-openai-tokens/): OpenAIが証券取引アプリRobinhoodの発行した『OpenAI tokens』に対し法的措置を警告。商標権侵害と消費者混乱を招く恐れがあるとして、即時停止を要求

---

## Lawrence's Insights

*※ここにLawrenceさんの手入力コメントを追加してください*

---
