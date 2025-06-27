# 2025年06月24日 AI NEWS TLDR

## Googleの遺伝子解析AIとLinkedIn求人6倍、AI業界の光と影

Googleは遺伝子制御の謎に迫る新AI「M-REGLE」を発表し、がんや難病解明への貢献が期待されます。

一方、LinkedInではAI関連求人が過去1年で6倍に増え、労働市場の構造変化が加速しています。

しかしその裏でAnthropicの「Claude Code」に深刻な脆弱性が発覚し、技術普及に伴うリスクも浮き彫りとなりました。

## 目次

1. Anthropic社のIDE拡張機能「Claude Code」において、WebSocket接続

2. GoogleのマルチモーダルAI「M-REGLE」、3種のデータで遺伝子制御を解明し、がん創薬を加速

3. LinkedInのデータが示すAI人材市場の沸騰、求人6倍・スキル追加20倍

4. Lyftの自動運転プロジェクトで直面した大規模データ処理の課題を解決するため

5. ウォルマート、150万人を支える内製AI「Element」で業務時間を最大67%削減

6. Persona社、AIで7500万件の採用詐欺をブロックディープフェイクによる潜入を阻止

7. 発覚、MetaはRunway買収交渉、Harveyは評価額50億ドルで資金調達

8. Traversal社のAI、数時間の障害分析を2分で完了因果推論でAI生成コードのバグも特定

9. Databricks、

10. Google検索やYouTubeを支えるAI「推論」技術、その実用化の核心に迫る

---

## 1. Anthropic社のIDE拡張機能「Claude Code」において、WebSocket接続

- Anthropic社のIDE拡張機能「Claude Code」において、WebSocket接続が任意のオリジンからの接続を許可してしまう深刻なセキュリティ脆弱性が発見されました。これにより、第三者による不正アクセスの危険性が生じています。

- この脆弱性を悪用されると、ユーザーが悪意のあるWebサイトを訪問するだけで、IDE内のファイル読み取り、作業内容の監視、さらには限定的なコード実行といった不正操作を許す可能性があり、深刻度は高いとされています。

- 影響を受けるのは、VSCodeやCursor、VSCodiumなどのIDEで脆弱なバージョンの「Claude Code for VSCode」を利用している開発者です。リスク回避のため、直ちに拡張機能を最新版へアップデートすることが強く推奨されています。

**Zenn_Llm** (https://zenn.dev/kimkiyong/articles/c60cab6dcb0260): Claude Code IDE拡張機能の重要なセキュリティ脆弱性 - 即座にアップデート推奨

## 2. GoogleのマルチモーダルAI「M-REGLE」、3種のデータで遺伝子制御を解明し、がん創薬を加速

- Google Researchは、遺伝子調節の解明を目指す新しいマルチモーダルAIモデル「M-REGLE」を開発しました。このモデルは、DNA配列、エピゲノム、遺伝子発現という3種類のデータを統合的に分析し、複雑な生命現象の根底にある遺伝子制御ネットワークの理解を深めます。

- M-REGLEは単一細胞データを利用し、特定の細胞種でどの調節エレメントがどの遺伝子を制御するかを高精度に予測します。これにより、従来のゲノムワイド関連解析（GWAS）では解明が難しかった、疾患関連の非コードDNA領域の機能的役割を特定できます。

- 本技術は、自己免疫疾患やがんといった複雑な疾患の遺伝的基盤解明に貢献します。疾患の原因となる細胞種や遺伝子経路を特定することで、将来的には精密医療の実現や新たな創薬ターゲットの発見につながることが期待されています。

> **Google Research** (https://research.google/blog/unlocking-rich-genetic-insights-through-multimodal-ai-with-m-regle/): Unlocking rich genetic insights through multimodal AI with M-REGLE

> **Google Blog** (https://blog.google/technology/ai/ask-a-techspert-what-is-inference/): Ask a techspert: What is inference?

## 3. LinkedInのデータが示すAI人材市場の沸騰、求人6倍・スキル追加20倍

- ビジネス特化型SNSのLinkedInにおいて、AIに言及する求人投稿が過去1年間で6倍に急増しました。同社のCEOであるRyan Roslansky氏が明らかにしたもので、企業側でのAI人材に対する需要が急速に高まっていることを示しています。

- 求人市場の動向と並行して、LinkedInユーザーが自身のプロフィールにAI関連スキルを追加する動きも顕著です。その数は過去1年間で20倍という驚異的な伸びを記録しており、労働者が市場の変化に積極的に対応していることが窺えます。

- 求人数の6倍増とスキル追加の20倍増というデータは、生成AIの台頭が労働市場に構造的な変革をもたらしていることを明確に示しています。企業と個人の両方でAIへの適応が不可欠な時代になっていることを浮き彫りにしました。

> **The Decoder** (https://the-decoder.com/ai-job-postings-on-linkedin-grew-sixfold-as-ai-skill-additions-to-profiles-soared-twentyfold/): AI job postings on LinkedIn grew sixfold as AI skill additions to profiles soared twentyfold

> **VentureBeat** (https://venturebeat.com/ai/75-million-deepfakes-blocked-persona-leads-the-corporate-fight-against-hiring-fraud/): 75 million deepfakes blocked: Persona leads the corporate fight against hiring fraud

## 4. Lyftの自動運転プロジェクトで直面した大規模データ処理の課題を解決するため

- Lyftの自動運転プロジェクトで直面した大規模データ処理の課題を解決するため、同プロジェクト出身のエンジニアが新会社Eventualを設立し、データ処理エンジン「Daft」を開発しました。

- Eventual社が開発した「Daft」は、Pythonで記述された分散クエリエンジンです。特に、自動運転開発で生じる画像やLiDARなどの大規模な非構造化・マルチモーダルデータの効率的な処理に特化しています。

- Lyftの自動運転部門では、多様なセンサーデータを扱うETLパイプラインがボトルネックでした。「Daft」は、このような複雑なデータソースを効率的に統合・処理するために設計されており、AIモデル開発の基盤を支えます。

> **TechCrunch** (https://techcrunch.com/2025/06/24/how-a-data-processing-problem-at-lyft-became-the-basis-for-eventual/): How a data processing problem at Lyft became the basis for Eventual

> **Zenn Dev** (https://zenn.dev/hiouchiy/articles/8d14adbdd416ba): Databricks Serverless GPU を使ってみる  ~MegatronLM編~

## 5. ウォルマート、150万人を支える内製AI「Element」で業務時間を最大67%削減

- 米小売大手ウォルマートは、特定のベンダーに依存しない独自のAIプラットフォーム「Element」を社内で構築しました。これにより、大規模言語モデル（大規模言語モデル（LLM））を含むAIアプリを迅速に開発・展開し、150万人の従業員を支援する基盤を確立しています。

- 「Element」上で開発されたAIアプリは、既に毎日300万件以上のクエリを処理しており、特定の計画タスクにかかる時間を最大67%削減するなど、業務効率化で顕著な成果を上げています。これにより従業員はより付加価値の高い業務に集中できます。

- この取り組みは、社内専門組織「AIファウンドリ」が主導しています。ビジネス課題の特定からソリューションの実装までを一貫して担い、従業員が実際に使いたくなるようなユーザー中心のAIツール開発を推進しています。

- 従業員向けアプリ「Me@Campus」などに生成AIを組み込むことで、現場のニーズに応えつつ、自然な形でAI技術の社内浸透を図っています。これは、テクノロジーの導入と従業員の定着を両立させる戦略的なアプローチです。

**Venturebeat_Ai** (https://venturebeat.com/ai/walmart-ai-foundry-ships-first-apps-3m-daily-queries-67-faster-planning/): How Walmart built an AI platform that makes it beholden to no one (and that 1.5M associates actually want to use)

## 6. Persona社、AIで7500万件の採用詐欺をブロックディープフェイクによる潜入を阻止

- 本人確認プラットフォームを提供するPersona社は、AIを活用した採用詐欺との戦いを主導し、これまでに7500万件ものディープフェイクを含む偽の求職者をブロックしたと発表しました。この実績は、リモート採用におけるセキュリティ脅威の深刻さを浮き彫りにしています。

- アメリカ企業では、ディープフェイク技術を悪用して身元を偽り、機密情報へのアクセスや金銭的利益を狙う採用詐欺が爆発的に増加しています。これにより、企業は深刻なセキュリティリスクに直面しており、採用プロセスの見直しを迫られています。

- 巧妙化する詐欺に対抗するため、企業はPersona社が提供するような高度な本人確認ツールの導入を進めています。これらのツールは、生体認証や公的書類のデジタル検証を組み合わせ、応募者が本人であることをリアルタイムで確認し、不正な潜入を防ぎます。

**Venturebeat_Ai** (https://venturebeat.com/ai/75-million-deepfakes-blocked-persona-leads-the-corporate-fight-against-hiring-fraud/): 75 million deepfakes blocked: Persona leads the corporate fight against hiring fraud

## 7. OpenAIのイヤホン開発が発覚、MetaはRunway買収交渉、Harveyは評価額50億ドルで資金調達

- OpenAIが初期に開発していたイヤホン型ハードウェアの存在が、iyO社との訴訟関連書類から明らかになりました。これは同社がソフトウェアだけでなく、AIを統合した独自のハードウェア分野への進出を初期から模索していたことを示唆しています。

- Meta社が、先進的な動画生成AIで知られるスタートアップ企業Runway AIとの買収交渉を行っていたと報じられました。この動きは、Metaが自社のエコシステムに高度な動画生成技術を取り込むことを目指す戦略の一環と見られています。

- 法律専門家向けのAIプラットフォームを提供するHarvey社が、企業評価額50億ドルという高い水準で3億ドルの資金調達を完了しました。専門分野に特化した生成AIソリューションに対する市場からの強い期待を反映しています。

> **Www Bayareatimes** (https://www.bayareatimes.com/p/israel-accuses-iran-of-breaching-ceasefire-announced-by-trump): Israel accuses Iran of breaching ceasefire announced by Trump

> **Stratechery** (https://stratechery.com/2025/checking-in-on-ai-and-the-big-five/?access_token=eyJhbGciOiJSUzI1NiIsImtpZCI6InN0cmF0ZWNoZXJ5LnBhc3Nwb3J0Lm9ubGluZSIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJzdHJhdGVjaGVyeS5wYXNzcG9ydC5vbmxpbmUiLCJhenAiOiJIS0xjUzREd1Nod1AyWURLYmZQV00xIiwiZW50Ijp7InVyaSI6WyJodHRwczovL3N0cmF0ZWNoZXJ5LmNvbS8yMDI1L2NoZWNraW5nLWluLW9uLWFpLWFuZC10aGUtYmlnLWZpdmUvIl19LCJleHAiOjE3NTMzMDc1MTEsImlhdCI6MTc1MDcxNTUxMSwiaXNzIjoiaHR0cHM6Ly9hcHAucGFzc3BvcnQub25saW5lL29hdXRoIiwic2NvcGUiOiJmZWVkOnJlYWQgYXJ0aWNsZTpyZWFkIGFzc2V0OnJlYWQgY2F0ZWdvcnk6cmVhZCBlbnRpdGxlbWVudHMgcG9kY2FzdCByc3MiLCJzdWIiOiIwMTk0YWE3NS05MzVhLTc1MGUtYTE3Mi1kNTVjMDkwZGY0MDAiLCJ1c2UiOiJhY2Nlc3MifQ.Wm2VIepj9qaKUp0Vlmp--gW0oa6ojY15XxCEJvjtS-ivGUXvP9DOqaFTkhzgbzFK9hL8h_iJtsoD38AsQzh0nQn2C1JIhq4f1E2YfKgaxSzRWMsJnyrroXEI_k4e5gsXCkKZm1dJcLSpkJFH7hqBc42dV43dw_gQL-Nrdh_LXVodUEPDbpPwvinfIQ1NoRayljcS9VEZZ2j4_8UDKIABXKCvhBLxzy6fXsfc4CQL_M4VvtHlSGta2sceTJUo8CVyKxABeaqU9DfmkWVpVjBhoRiXJWzy_slD0OCBTzmzw318gLiD_MNcIHr2uwIIllgDBpHa9WQRdKBj_WBsV6QZoQ): Checking In on AI and the Big Five

## 8. Traversal社のAI、数時間の障害分析を2分で完了因果推論でAI生成コードのバグも特定

- Traversal社は、システム障害時の根本原因分析（RCA）を劇的に効率化するAIエージェントを開発しました。従来エンジニアチームが数時間かけていた作業を、わずか2〜4分で完了させ、問題の根本にあるログやコード変更を特定します。

- 同社の技術は、共同創業者が持つ因果推論や遺伝子制御ネットワークに関する学術研究が基盤です。このアプローチは、医療における診断プロセスのように、システムの膨大なデータから因果関係をたどり、障害の根本原因を正確に突き止めます。

- AIによるコード生成が普及する中、人間が直接記述していないコードのデバッグという新たな課題が深刻化しています。Traversal社のAI診断ツールは、このような複雑な環境でソフトウェアの信頼性を維持するために不可欠なソリューションとなります。

**Sequoia_Youtube** (https://www.youtube.com/watch?v=7hBG5ShQ2BA): From DevOps ‘Heart Attacks’ to AI-Powered Diagnostics With Traversal’s AI Agents

## 9. Databricks、NVIDIA A10搭載サーバーレスGPUを発表MegatronLMの分散学習は可能か検証

- Databricksは、Data + AI Summit 2025で新機能「Serverless GPU」を発表し、現在ベータ版として提供を開始しました。この機能により、ユーザーはサーバー管理なしでオンデマンドにGPUリソースを利用でき、現時点では単一のNVIDIA A10 GPUが利用可能です。

- 本機能は将来的に、より高性能なNVIDIA H100 GPUのマルチGPU構成までサポートを拡張する計画です。これにより、大規模なモデルのトレーニングや推論といった、さらに計算負荷の高いAIワークロードにもサーバーレス環境で対応可能となる見込みです。

- 記事では、この新しいServerless GPU環境の実用性を検証するため、一般的なライブラリだけでなく、大規模言語モデルの分散学習フレームワークであるMegatronLMが動作するかを確認しています。これは、複雑なセットアップを要するフレームワークへの対応力を測る試みです。

**Zenn_Llm** (https://zenn.dev/hiouchiy/articles/8d14adbdd416ba): Databricks Serverless GPU を使ってみる  ~MegatronLM編~

## 10. Google検索やYouTubeを支えるAI「推論」技術、その実用化の核心に迫る

- AIにおける「推論（Inference）」とは、学習済みモデルが未知の新しいデータに対して予測や判断を行うプロセスです。これは、モデルを構築する「トレーニング（学習）」フェーズとは区別される、AIを実用化するための核心的なステップと位置づけられています。

- Google検索でのクエリ意図解釈、Googleフォトでの画像認識、YouTubeでの動画推薦など、多くのGoogle製品がこの推論技術を活用しています。これにより、ユーザーの入力に対してリアルタイムで最適な結果を返すことが可能になります。

- このプロセスは、人間が過去の経験から現在の状況を判断する認知プロセスに類似しています。AIモデルも同様に、トレーニングで学んだ膨大なデータパターンを基に、新しい入力に対して「猫の画像」を識別したり、最適な翻訳を生成したりします。

**Google_Gemini_Blog** (https://blog.google/technology/ai/ask-a-techspert-what-is-inference/): Ask a techspert: What is inference?

---

## Lawrence's Insights

*※ここにLawrenceさんの手入力コメントを追加してください*

---