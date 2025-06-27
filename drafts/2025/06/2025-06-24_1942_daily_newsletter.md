# 2025年06月24日 AI NEWS TLDR

## Googleの量子革命、DatabricksのGPUインフラ、過熱するAI人材市場

Google Quantum AIが量子誤り訂正で「ブレークイーブン」を実証し、耐故障性量子コンピュータ実現へ大きく前進しました。

一方、DatabricksはNVIDIA A10搭載の「Serverless GPU」を発表し、AI開発インフラを強化しています。

この技術革新を背景に、LinkedInではAI求人が過去1年で6倍に増加

## 目次

1. Google、49量子ビットで量子エラー訂正の壁を突破高効率な17量子ビット「カラー符号」も実証

2. LinkedInのAI求人6倍増、スキル追加は20倍に労働市場でAIシフトが加速

3. Databricksの新機能「Serverless…

4. Anthropic、のClaude Code拡張機能に脆弱性、

5. GoogleのAI「M-REGLE」がゲノムと画像を統合、がん等の疾患原因を解明へ

6. 裁判資料で判明！OpenAI、io社と初のAIハードウェアを開発市場投入は1年以上先か

7. Traversal社は、システム障害の根本原因分析(RCA)を自動化するAIエージェント

8. 米国運輸省道路交通安全局（NHTSA）が、テスラのロボタクシーに関する安全性への懸念から同社に接触し

---

## 1. Google、49量子ビットで量子エラー訂正の壁を突破高効率な17量子ビット「カラー符号」も実証

- Google Quantum AIは、量子誤り訂正において画期的な成果を発表しました。複数の物理量子ビットから構成される論理量子ビットのエラー率が、個々の物理量子ビットのエラー率を初めて下回る「ブレークイーブン」を実験的に実証し、耐故障性量子コンピュータ実現への道筋を示しました。

- 実験では、49個の物理量子ビットを用いて1つの論理量子ビットを構成する「サーフェス符号」を使用しました。その結果、論理エラー率2.914%を達成し、物理コンポーネントのエラー率3.028%をわずかに下回ることに成功しました。

- サーフェス符号に加え、より少ない17個の物理量子ビットで論理量子ビットを構成できる、より効率的な「カラー符号」の実験にも成功しました。これは将来の量子コンピュータの規模拡大と性能向上に貢献する重要な技術として期待されています。

- この成果は、量子計算における最大の課題である「デコヒーレンス」によるエラーを能動的に訂正する能力を実証したものです。Nature誌にも掲載され、実用的な大規模量子コンピュータの構築に向けた重要なマイルストーンと位置づけられています。

> **Google Research** (https://research.google/blog/a-colorful-quantum-future/): A colorful quantum future

> **TechCrunch** (https://techcrunch.com/2025/06/23/google-introduces-ai-mode-to-users-in-india/): Google introduces AI mode to users in India

> **VentureBeat** (https://venturebeat.com/ai/beyond-static-ai-mits-new-framework-lets-models-teach-themselves/): Beyond static AI: MIT’s new framework lets models teach themselves

## 2. LinkedInのAI求人6倍増、スキル追加は20倍に労働市場でAIシフトが加速

- ビジネス特化型SNSのLinkedInにおいて、AIに言及する求人投稿が過去1年間で6倍に急増したことが、同社のCEOであるRyan Roslansky氏によって明らかにされました。これは、企業がAI技術を事業に組み込む動きを加速させていることを示唆しています。

- 求人数の増加と並行して、LinkedInユーザーが自身のプロフィールにAI関連スキルを追加する動きも顕著です。その数は20倍にも達しており、労働市場におけるAIスキルの重要性が急速に高まっている現状を反映しています。

- この求人数の6倍増とスキル追加数の20倍増というデータは、企業と個人の両サイドでAIへの対応が急務となっていることを示しています。生成AIの普及を背景に、労働市場全体でAIリテラシーが不可欠な要素になりつつあることを裏付けるものです。

- Meta社は、最新AIモデルLlama 4が期待外れだったことを受け、AI分野での遅れを取り戻すべくCEOのマーク・ザッカーバーグ氏が自ら人材獲得に奔走しています。新設する「Superintelligence lab」のため、巨額の報酬提示やスタートアップ買収も検討中です。

> **The Decoder** (https://the-decoder.com/ai-job-postings-on-linkedin-grew-sixfold-as-ai-skill-additions-to-profiles-soared-twentyfold/): AI job postings on LinkedIn grew sixfold as AI skill additions to profiles soared twentyfold

> **Stratechery** (https://stratechery.com/2025/checking-in-on-ai-and-the-big-five/?access_token=eyJhbGciOiJSUzI1NiIsImtpZCI6InN0cmF0ZWNoZXJ5LnBhc3Nwb3J0Lm9ubGluZSIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJzdHJhdGVjaGVyeS5wYXNzcG9ydC5vbmxpbmUiLCJhenAiOiJIS0xjUzREd1Nod1AyWURLYmZQV00xIiwiZW50Ijp7InVyaSI6WyJodHRwczovL3N0cmF0ZWNoZXJ5LmNvbS8yMDI1L2NoZWNraW5nLWluLW9uLWFpLWFuZC10aGUtYmlnLWZpdmUvIl19LCJleHAiOjE3NTMzMDc1MTEsImlhdCI6MTc1MDcxNTUxMSwiaXNzIjoiaHR0cHM6Ly9hcHAucGFzc3BvcnQub25saW5lL29hdXRoIiwic2NvcGUiOiJmZWVkOnJlYWQgYXJ0aWNsZTpyZWFkIGFzc2V0OnJlYWQgY2F0ZWdvcnk6cmVhZCBlbnRpdGxlbWVudHMgcG9kY2FzdCByc3MiLCJzdWIiOiIwMTk0YWE3NS05MzVhLTc1MGUtYTE3Mi1kNTVjMDkwZGY0MDAiLCJ1c2UiOiJhY2Nlc3MifQ.Wm2VIepj9qaKUp0Vlmp--gW0oa6ojY15XxCEJvjtS-ivGUXvP9DOqaFTkhzgbzFK9hL8h_iJtsoD38AsQzh0nQn2C1JIhq4f1E2YfKgaxSzRWMsJnyrroXEI_k4e5gsXCkKZm1dJcLSpkJFH7hqBc42dV43dw_gQL-Nrdh_LXVodUEPDbpPwvinfIQ1NoRayljcS9VEZZ2j4_8UDKIABXKCvhBLxzy6fXsfc4CQL_M4VvtHlSGta2sceTJUo8CVyKxABeaqU9DfmkWVpVjBhoRiXJWzy_slD0OCBTzmzw318gLiD_MNcIHr2uwIIllgDBpHa9WQRdKBj_WBsV6QZoQ): Checking In on AI and the Big Five

## 3. Databricksの新機能「Serverless GPU」ベータ版公開！A10でMegatronLMの動作を検証

- DatabricksがData + AI Summit 2025で新機能「Serverless GPU」を発表しました。2025年6月18日現在、ベータ版として提供されており、オンデマンドで単一のNVIDIA A10 GPUを利用可能です。

- 本機能は将来的には、より高性能なNVIDIA H100によるマルチGPU構成までサポートを拡張する計画です。これにより、大規模なAIモデルのトレーニングや推論がより容易になることが期待されます。

- 記事では、この新しいServerless GPU環境上で、大規模言語モデルのフレームワークであるMegatronLMが動作するかを検証しています。これは、新機能の実用性をより複雑なユースケースで確認する試みです。

- 具体的な利用方法として、Databricksのノートブック環境でアクセラレータとしてGPU（A10）を選択し、クラスターにアタッチする簡単な操作が紹介されており、手軽にGPUリソースを活用できる点が示されています。

> **Zenn Dev** (https://zenn.dev/hiouchiy/articles/8d14adbdd416ba): Databricks Serverless GPU を使ってみる  ~MegatronLM編~

> **YouTube** (https://www.youtube.com/shorts/E0NJyUy8kc8): If ChatGPT were your wingman…

## 4. AnthropicのClaude Code拡張機能に脆弱性、VSCode内のファイル窃取やコード実行の危険

- Anthropic社のIDE拡張機能「Claude Code」において、WebSocket接続が任意のオリジンからの接続を許可してしまう深刻なセキュリティ脆弱性が発見されました。これにより、第三者による不正なアクセスが可能となります。

- この脆弱性を悪用されると、ユーザーが悪意のあるWebサイトを訪問するだけで、IDE内のファイル読み取り、作業内容の監視、さらには限定的なコード実行といった被害を受ける可能性があります。

- 脆弱性の影響を受けるのは、VSCodeやCursor、VSCodiumなどのVSCode系IDEで利用されている「Claude Code for VSCode」拡張機能です。開発者には、リスク回避のため直ちに最新バージョンへのアップデートが強く推奨されています。

> **Zenn Llm** (https://zenn.dev/kimkiyong/articles/c60cab6dcb0260): Claude Code IDE拡張機能の重要なセキュリティ脆弱性 - 即座にアップデート推奨

## 5. GoogleのAI「M-REGLE」がゲノムと画像を統合、がん等の疾患原因を解明へ

- Google Researchは、マルチモーダルAIモデル「M-REGLE」を開発しました。このモデルは、ゲノム配列と組織学画像という異なるデータを統合し、疾患リスクに関わる非コードDNA領域と遺伝子との関連性を高精度に予測することを目的としています。

- M-REGLEは、特定の非コードDNA領域が活性化している細胞の視覚的特徴とゲノム配列情報を同時に学習します。これにより、どの細胞タイプでどのエンハンサーが標的遺伝子を制御しているかを、従来の手法よりも正確に特定することが可能になりました。

- この技術は、がんや自己免疫疾患など、多くの疾患に関連する遺伝的変異の機能を解明する上で重要な進歩です。将来的には、個々の患者に合わせた精密医療や新しい治療法の開発に貢献することが期待されています。

- Traversal社は、システム障害の根本原因分析(RCA)を自動化するAIエージェントを開発しました。従来エンジニアチームが数時間かけていた特定作業をわずか2-4分で完了させ、DevOpsの効率を劇的に向上させます。この技術は、創業者たちの因果推論に関する学術研究を応用したものです。

> **Google Research** (https://research.google/blog/unlocking-rich-genetic-insights-through-multimodal-ai-with-m-regle/): Unlocking rich genetic insights through multimodal AI with M-REGLE

> **YouTube** (https://www.youtube.com/watch?v=7hBG5ShQ2BA): From DevOps ‘Heart Attacks’ to AI-Powered Diagnostics With Traversal’s AI Agents

> **VentureBeat** (https://venturebeat.com/ai/salesforce-launches-agentforce-3-with-ai-agent-observability-and-mcp-support/): Salesforce launches Agentforce 3 with AI agent observability and MCP support

## 6. 裁判資料で判明！OpenAI、io社と初のAIハードウェアを開発市場投入は1年以上先か

- OpenAIが初のAIハードウェアデバイスを開発中であることが、訴訟関連の裁判所提出書類から明らかになりました。製品の市場投入は少なくとも1年以上先と見られており、同社のハードウェア市場への参入計画が初期段階にあることを示唆しています。

- 開発中のデバイスは、当初噂されていたインイヤー型製品に限定されず、他の様々なフォームファクター（形状）も検討されていることが示唆されています。これにより、ウェアラブルや家庭用アシスタントなど、より広範な製品カテゴリの可能性が浮上しました。

- 記事タイトルによると、このAIデバイス開発は「io」という企業との初期段階の協力関係のもとで進められているようです。訴訟資料を通じてこの協力関係が明らかになったことは、OpenAIが外部パートナーとの連携を模索していることを示しています。

- ディズニーは、自社の著作権で保護されたキャラクターを無許可でAIモデルの学習データなどに使用するAI企業に対し、法的な対抗措置を強化しています。これは、知的財産の価値を守り、不正利用を断固として許さないという同社の姿勢を示すものです。

> **TechCrunch** (https://techcrunch.com/2025/06/23/court-filings-reveal-openai-and-ios-early-work-on-an-ai-device/): Court filings reveal OpenAI and io’s early work on an AI device

> **The Decoder** (https://the-decoder.com/disney-is-in-talks-with-openai-about-possible-partnerships-involving-its-characters/): Disney is in talks with OpenAI about possible partnerships involving its characters

## 7. Traversal社は、システム障害の根本原因分析(RCA)を自動化するAIエージェント

- Traversal社は、システム障害の根本原因分析(RCA)を自動化するAIエージェントを開発しました。従来エンジニアチームが数時間かけていた特定作業をわずか2-4分で完了させ、DevOpsの効率を劇的に向上させます。この技術は、創業者たちの因果推論に関する学術研究を応用したものです。

- 同社のAIエージェントは、複雑なシステムの依存関係マップを体系的に探索し、問題を引き起こしているログやコード変更を正確に特定します。大規模言語モデル(大規模言語モデル（LLM）)と観測可能性データを活用することで、高精度なトラブルシューティングを実現し、障害対応の迅速化に貢献します。

- AIによるコード生成が普及する中、人間が直接開発に関与しないコードのデバッグという新たな課題が浮上しています。TraversalのAI診断ツールは、このような複雑な環境下で信頼性の高いソフトウェアを維持するために不可欠な技術となり、SREチームの未来を再定義する可能性を秘めています。

> **Sequoia Youtube** (https://www.youtube.com/watch?v=7hBG5ShQ2BA): From DevOps ‘Heart Attacks’ to AI-Powered Diagnostics With Traversal’s AI Agents
> 【翻訳】Traversal社が開発したAIエージェントは、システム障害の根本原因分析(RCA)を自動化します。因果推論の学術研究を応用し、従来数時間を要した特定作業をわずか2-4分に短縮、DevOpsチームの効率を劇的に向上させます。

## 8. 米国運輸省道路交通安全局（NHTSA）が、テスラのロボタクシーに関する安全性への懸念から同社に接触し

- 米国運輸省道路交通安全局（NHTSA）が、テスラのロボタクシーに関する安全性への懸念から同社に接触しました。この動きは、オンライン上で多数投稿された、同社の車両が交通法規に違反しているように見える動画がきっかけとなっています。

- 問題となっているのは、テキサス州サウスオースティンで限定的に提供されているロボタクシーサービスです。公開された動画では、車両が交通法規に違反する様子が捉えられており、規制当局の注意を引く事態となりました。

- テスラは現在、このロボタクシーサービスを招待された顧客のみに提供しており、より広範な一般公開に向けたテスト段階にあります。今回のNHTSAの介入は、この試験運用が規制当局の厳格な監視下にあることを示しています。

> **TechCrunch** (https://techcrunch.com/2025/06/23/teslas-robotaxis-have-already-caught-the-attention-of-federal-safety-regulators/): Tesla’s robotaxis have already caught the attention of federal safety regulators
> 【翻訳】テスラのロボタクシーに対し、米国運輸省道路交通安全局（NHTSA）が安全性への懸念から接触しました。この動きは、オンライン上で同社の車両が交通法規に違反しているように見える動画が多数投稿されたことがきっかけとなっています。

---

## Lawrence's Insights

*※ここにLawrenceさんの手入力コメントを追加してください*

---