# 2025年06月24日 AI NEWS TLDR

## OpenAIのGPT-4oからGoogleの量子AIまで、技術革新の最前線

OpenAIは、GPT-4oがリアルタイム音声会話で人間を支援するデモを公開し、AIが日常の相棒となる未来を提示しました。

一方Google Quantum AIは量子誤り訂正で歴史的成果を上げ、実用的な量子コンピュータの実現を大きく前進させています。

さらにTraversal社は、数時間の障害分析を2〜4分に短縮するAIでDevOpsの現場に変革をもたらすな…

## 目次

1. OpenAI、が示すGPT-4oの未来ChatGPTがリアルタイム音声で最強の「ウィングマン」

2. Google、49量子ビットで量子誤り訂正の壁を突破エラー率の「損益分岐点」を初めて超える

3. Traversal社は、DevOpsにおけるシステム障害時の根本原因分析（RCA

4. Google、のAI検索「AI mode」がインド上陸Search Labsで実験的に提供開始

5. の「Claude Code」に深刻な脆弱性

6. Salesforce社が、AIエージェントの運用

7. LinkedInが明かすAI人材争奪戦：求人は6倍増、スキル追加は20倍に急伸

8. Serverless GPUベータ版を提供開始オンデマンドA10でMegatronLMを動かす

9. 裁判資料で発覚OpenAI、初のAIデバイス開発に着手、市場投入は1年以上先か

10. テスラ、ロボタクシーの安全性に黄信号米NHTSAが交通違反で本格調査へ

---

## 1. OpenAIが示すGPT-4oの未来ChatGPTがリアルタイム音声で最強の「ウィングマン」

- OpenAIが公式YouTubeで公開したショート動画は、ChatGPTをリアルタイムの会話アシスタントとして活用する新たな使用例を提示しました。社交の場で緊張する人を助ける「ウィングマン」として機能する様子が描かれています。

- このデモは、GPT-4oなどで実装された高度なリアルタイム音声対話機能の能力を強調するものです。ユーザーが音声で助けを求めると、ChatGPTが即座に状況を理解し、遅延なく自然な口調で応答する様子が確認できます。

- 動画内でChatGPTは、相手の女性が読んでいるジェイン・オースティンの本を特定し、それに基づいた知的で気の利いた会話の切り出し方を提案しました。これはAIの高度な文脈認識能力とパーソナライズされた支援の可能性を示唆しています。

- この動画は、AIの高度な技術を「恋愛」という身近で共感を呼びやすいテーマに落とし込むマーケティング戦略の一環です。技術的な詳細ではなく、実生活での具体的な利便性を一般ユーザーに分かりやすく伝えています。

> **Openai Youtube** (https://www.youtube.com/shorts/E0NJyUy8kc8): If ChatGPT were your wingman…
> 【翻訳】OpenAIが公式YouTubeで公開した動画は、同社のAI「ChatGPT」がリアルタイムの会話アシスタントとして機能する新たな活用法を提示しました。社交の場で緊張する人を助ける「ウィングマン」としての未来が描かれています。

> **YouTube** (https://www.youtube.com/shorts/E0NJyUy8kc8): If ChatGPT were your wingman…

> **VentureBeat** (https://venturebeat.com/ai/beyond-static-ai-mits-new-framework-lets-models-teach-themselves/): Beyond static AI: MIT’s new framework lets models teach themselves

## 2. Google、49量子ビットで量子誤り訂正の壁を突破エラー率の「損益分岐点」を初めて超える

- Google Quantum AIは、量子誤り訂正において歴史的なマイルストーンを達成したと発表しました。初めて論理量子ビットのエラー率が、それを構成する物理量子ビットの性能を上回り、実用的な量子コンピュータ実現に不可欠な「損益分岐点」を突破しました。

- この実験では「表面符号（surface code）」と呼ばれる誤り訂正技術が用いられました。物理量子ビットの数を17個から49個へとスケールアップさせることで、論理量子ビットのエラー率が実際に低減することを実証し、符号の規模拡大が性能向上に繋がることを証明しました。

- この成果は、スケーラブルな量子誤り訂正が理論だけでなく現実のハードウェアで機能することを示した点で画期的です。これにより、Googleは100万個の物理量子ビットで1,000個の論理量子ビットを構築するというロードマップの重要な段階をクリアしました。

- DatabricksがData + AI Summit 2025で発表した新機能「Serverless GPU」が、ベータ版として利用可能になりました。これにより、ユーザーはサーバー管理を意識することなく、オンデマンドでGPUリソースをノートブックにアタッチできます。

> **Google Research Blog** (https://research.google/blog/a-colorful-quantum-future/): A colorful quantum future
> 【翻訳】AI技術の重要な進展が発表。業界動向と将来への影響を詳細に解説。

> **Google Research** (https://research.google/blog/a-colorful-quantum-future/): A colorful quantum future

> **Zenn Dev** (https://zenn.dev/hiouchiy/articles/8d14adbdd416ba): Databricks Serverless GPU を使ってみる  ~MegatronLM編~

> **TechCrunch** (https://techcrunch.com/2025/06/23/google-introduces-ai-mode-to-users-in-india/): Google introduces AI mode to users in India

## 3. Traversal社は、DevOpsにおけるシステム障害時の根本原因分析（RCA

- Traversal社は、DevOpsにおけるシステム障害時の根本原因分析（RCA）を劇的に変革するAIエージェントを開発しました。共同創業者Anish Agarwal氏とRaj Agrawal氏が主導し、従来エンジニアチームが数時間要していた作業をわずか2〜4分に短縮します。

- このAIエージェントは、創業者らの因果推論や遺伝子制御ネットワークに関する学術研究が基盤です。複雑なシステムの依存関係マップを体系的に探索し、障害の引き金となったログや問題のあるコード変更を正確に特定する能力を持ちます。

- AIによるコード生成が普及する中、人間が直接記述していないコードのデバッグは新たな課題となっています。Traversalの技術は、このような環境下で大規模ソフトウェアの信頼性を維持するために不可欠なAI主導のトラブルシューティングを提供します。

- Salesforce社が、AIエージェントの運用を強化する新プラットフォーム「Agentforce 3」を発表しました。このバージョンでは、AIエージェントのオブザーバビリティ（可観測性）が主要機能として追加されています。

> **Sequoia Youtube** (https://www.youtube.com/watch?v=7hBG5ShQ2BA): From DevOps ‘Heart Attacks’ to AI-Powered Diagnostics With Traversal’s AI Agents
> 【翻訳】Traversal社が開発したAIエージェントは、DevOpsにおける「心臓発作」とも言えるシステム障害の根本原因分析を劇的に変革します。この技術により、従来エンジニアが数時間要していた分析作業が、わずか2〜4分に短縮されます。

> **YouTube** (https://www.youtube.com/watch?v=7hBG5ShQ2BA): From DevOps ‘Heart Attacks’ to AI-Powered Diagnostics With Traversal’s AI Agents

> **VentureBeat** (https://venturebeat.com/ai/salesforce-launches-agentforce-3-with-ai-agent-observability-and-mcp-support/): Salesforce launches Agentforce 3 with AI agent observability and MCP support

## 4. GoogleのAI検索「AI mode」がインド上陸Search Labsで実験的に提供開始

- Googleは、Q&A形式のAI検索ツール「AI mode」をインドのユーザー向けに提供開始しました。これは同社のAI機能のグローバル展開における重要な一歩となります。

- この新機能はまだ実験段階にあり、利用を希望するユーザーはGoogleの実験的機能プラットフォームである「Search Labs」を通じてオプトインする必要があります。

- オプトインしたユーザーは、現時点では英語でAIに質問を投げかけることが可能です。Googleは他の言語への対応についてはまだ明らかにしていません。

> **TechCrunch** (https://techcrunch.com/2025/06/23/google-introduces-ai-mode-to-users-in-india/): Google introduces AI mode to users in India
> 【翻訳】Googleは、Q&A形式のAI検索ツール「AI mode」をインドのユーザー向けに提供開始しました。これは同社のAI機能をグローバルに展開する上で重要な一歩となり、巨大市場でのサービス拡大を目指します。

## 5. Anthropicの「Claude Code」に深刻な脆弱性、VSCode経由でコード漏洩の恐れ即時更新が必須

- Anthropic社のIDE拡張機能「Claude Code」において、WebSocket接続が任意のオリジンからの接続を許可してしまう深刻なセキュリティ脆弱性が発見されました。これにより、第三者がユーザーのIDE環境へ不正にアクセスできる状態でした。

- この脆弱性を悪用されると、ユーザーが悪意のあるWebサイトを訪問するだけで、IDE内のファイル読み取り、作業内容の監視、限定的なコード実行といった被害を受ける可能性があります。機密情報やソースコードの漏洩リスクが指摘されています。

- 影響を受けるのはVSCode、Cursor、VSCodiumなどのVSCode系IDEで利用されている特定のバージョンの拡張機能です。開発元は既に対策済みバージョンを公開しており、全ユーザーに対して即時のアップデートを強く推奨しています。

> **Zenn Llm** (https://zenn.dev/kimkiyong/articles/c60cab6dcb0260): Claude Code IDE拡張機能の重要なセキュリティ脆弱性 - 即座にアップデート推奨

## 6. Salesforce社が、AIエージェントの運用

- Salesforce社が、AIエージェントの運用を強化する新プラットフォーム「Agentforce 3」を発表しました。このバージョンでは、AIエージェントのオブザーバビリティ（可観測性）が主要機能として追加されています。

- 新搭載のオブザーバビリティ機能により、企業はAIエージェントの動作やパフォーマンスをリアルタイムで詳細に可視化・監視することが可能になります。これにより、問題の迅速な特定と解決が促進されます。

- Agentforce 3は、MCP（Model Connector Protocol）をネイティブでサポートしており、異なるAIモデルやシステム間でのセキュアな相互運用性を確保します。これにより、柔軟なAIソリューションの構築が実現します。

- ビジネス特化型SNSのLinkedIn上で、AIに言及する求人情報が過去1年間で6倍に急増したことが、同社のCEOであるRyan Roslansky氏によって明らかにされました。これは、各業界でAI技術の導入が加速し、専門知識を持つ人材への需要が急速に高まっていることを示しています。

> **Venturebeat Ai** (https://venturebeat.com/ai/salesforce-launches-agentforce-3-with-ai-agent-observability-and-mcp-support/): Salesforce launches Agentforce 3 with AI agent observability and MCP support
> 【翻訳】Salesforce社が、新プラットフォーム「Agentforce 3」を発表しました。AIエージェントの運用を強化するため、その動作を詳細に把握できる「オブザーバビリティ（可観測性）」を主要機能として追加しています。

> **VentureBeat** (https://venturebeat.com/ai/salesforce-launches-agentforce-3-with-ai-agent-observability-and-mcp-support/): Salesforce launches Agentforce 3 with AI agent observability and MCP support

> **The Decoder** (https://the-decoder.com/ai-job-postings-on-linkedin-grew-sixfold-as-ai-skill-additions-to-profiles-soared-twentyfold/): AI job postings on LinkedIn grew sixfold as AI skill additions to profiles soared twentyfold

> **Stratechery** (https://stratechery.com/2025/checking-in-on-ai-and-the-big-five/?access_token=eyJhbGciOiJSUzI1NiIsImtpZCI6InN0cmF0ZWNoZXJ5LnBhc3Nwb3J0Lm9ubGluZSIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJzdHJhdGVjaGVyeS5wYXNzcG9ydC5vbmxpbmUiLCJhenAiOiJIS0xjUzREd1Nod1AyWURLYmZQV00xIiwiZW50Ijp7InVyaSI6WyJodHRwczovL3N0cmF0ZWNoZXJ5LmNvbS8yMDI1L2NoZWNraW5nLWluLW9uLWFpLWFuZC10aGUtYmlnLWZpdmUvIl19LCJleHAiOjE3NTMzMDc1MTEsImlhdCI6MTc1MDcxNTUxMSwiaXNzIjoiaHR0cHM6Ly9hcHAucGFzc3BvcnQub25saW5lL29hdXRoIiwic2NvcGUiOiJmZWVkOnJlYWQgYXJ0aWNsZTpyZWFkIGFzc2V0OnJlYWQgY2F0ZWdvcnk6cmVhZCBlbnRpdGxlbWVudHMgcG9kY2FzdCByc3MiLCJzdWIiOiIwMTk0YWE3NS05MzVhLTc1MGUtYTE3Mi1kNTVjMDkwZGY0MDAiLCJ1c2UiOiJhY2Nlc3MifQ.Wm2VIepj9qaKUp0Vlmp--gW0oa6ojY15XxCEJvjtS-ivGUXvP9DOqaFTkhzgbzFK9hL8h_iJtsoD38AsQzh0nQn2C1JIhq4f1E2YfKgaxSzRWMsJnyrroXEI_k4e5gsXCkKZm1dJcLSpkJFH7hqBc42dV43dw_gQL-Nrdh_LXVodUEPDbpPwvinfIQ1NoRayljcS9VEZZ2j4_8UDKIABXKCvhBLxzy6fXsfc4CQL_M4VvtHlSGta2sceTJUo8CVyKxABeaqU9DfmkWVpVjBhoRiXJWzy_slD0OCBTzmzw318gLiD_MNcIHr2uwIIllgDBpHa9WQRdKBj_WBsV6QZoQ): Checking In on AI and the Big Five

## 7. LinkedInが明かすAI人材争奪戦：求人は6倍増、スキル追加は20倍に急伸

- ビジネス特化型SNSのLinkedIn上で、AIに言及する求人情報が過去1年間で6倍に急増したことが、同社のCEOであるRyan Roslansky氏によって明らかにされました。これは、各業界でAI技術の導入が加速し、専門知識を持つ人材への需要が急速に高まっていることを示しています。

- 求職者側でもAIスキルへの関心が飛躍的に高まっており、自身のLinkedInプロフィールにAI関連のスキルを追加するユーザーの動きは、同期間で20倍という驚異的な伸びを記録しました。これは労働者が市場価値を高めるために積極的に新技術を習得している現状を反映しています。

- この求人数の6倍増とスキル追加の20倍増という2つのデータは、AIが労働市場の構造を大きく変えつつあることを明確に示唆しています。企業の人材獲得競争が激化する一方で、労働者にとってはAIスキルの有無がキャリアを左右する重要な要素となりつつあります。

- AI開発に不可欠な計算インフラが、ごく一部の国に極端に集中している現状が指摘されています。この偏在により、アフリカや南米などの多くの国々が、グローバルなAI開発競争から事実上取り残されている状況です。

> **The Decoder** (https://the-decoder.com/ai-job-postings-on-linkedin-grew-sixfold-as-ai-skill-additions-to-profiles-soared-twentyfold/): AI job postings on LinkedIn grew sixfold as AI skill additions to profiles soared twentyfold
> 【翻訳】ビジネスSNSのLinkedIn上で、AI関連の求人情報が過去1年間で6倍に急増しました。一方、プロフィールにAIスキルを追加する動きは20倍に達しており、AI技術をめぐる人材需要とスキル習得が共に急拡大していることを示しています。

> **The Decoder** (https://the-decoder.com/ai-job-postings-on-linkedin-grew-sixfold-as-ai-skill-additions-to-profiles-soared-twentyfold/): AI job postings on LinkedIn grew sixfold as AI skill additions to profiles soared twentyfold

> **The Decoder** (https://the-decoder.com/african-and-south-american-countries-are-almost-entirely-excluded-from-global-ai-development/): African and South American countries are almost entirely excluded from global AI development

> **Stratechery** (https://stratechery.com/2025/checking-in-on-ai-and-the-big-five/?access_token=eyJhbGciOiJSUzI1NiIsImtpZCI6InN0cmF0ZWNoZXJ5LnBhc3Nwb3J0Lm9ubGluZSIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJzdHJhdGVjaGVyeS5wYXNzcG9ydC5vbmxpbmUiLCJhenAiOiJIS0xjUzREd1Nod1AyWURLYmZQV00xIiwiZW50Ijp7InVyaSI6WyJodHRwczovL3N0cmF0ZWNoZXJ5LmNvbS8yMDI1L2NoZWNraW5nLWluLW9uLWFpLWFuZC10aGUtYmlnLWZpdmUvIl19LCJleHAiOjE3NTMzMDc1MTEsImlhdCI6MTc1MDcxNTUxMSwiaXNzIjoiaHR0cHM6Ly9hcHAucGFzc3BvcnQub25saW5lL29hdXRoIiwic2NvcGUiOiJmZWVkOnJlYWQgYXJ0aWNsZTpyZWFkIGFzc2V0OnJlYWQgY2F0ZWdvcnk6cmVhZCBlbnRpdGxlbWVudHMgcG9kY2FzdCByc3MiLCJzdWIiOiIwMTk0YWE3NS05MzVhLTc1MGUtYTE3Mi1kNTVjMDkwZGY0MDAiLCJ1c2UiOiJhY2Nlc3MifQ.Wm2VIepj9qaKUp0Vlmp--gW0oa6ojY15XxCEJvjtS-ivGUXvP9DOqaFTkhzgbzFK9hL8h_iJtsoD38AsQzh0nQn2C1JIhq4f1E2YfKgaxSzRWMsJnyrroXEI_k4e5gsXCkKZm1dJcLSpkJFH7hqBc42dV43dw_gQL-Nrdh_LXVodUEPDbpPwvinfIQ1NoRayljcS9VEZZ2j4_8UDKIABXKCvhBLxzy6fXsfc4CQL_M4VvtHlSGta2sceTJUo8CVyKxABeaqU9DfmkWVpVjBhoRiXJWzy_slD0OCBTzmzw318gLiD_MNcIHr2uwIIllgDBpHa9WQRdKBj_WBsV6QZoQ): Checking In on AI and the Big Five

## 8. Databricks、Serverless GPUベータ版を提供開始オンデマンドA10でMegatronLMを動かす

- DatabricksがData + AI Summit 2025で発表した新機能「Serverless GPU」が、ベータ版として利用可能になりました。これにより、ユーザーはサーバー管理を意識することなく、オンデマンドでGPUリソースをノートブックにアタッチできます。

- 現行のベータ版では、単一のNVIDIA A10 GPUをオンデマンドで利用できます。将来的には、より高性能なNVIDIA H100によるマルチGPU構成への拡張が計画されており、大規模なAIモデル開発への対応強化が期待されます。

- 本記事では、この新環境の実用性を検証するため、一般的なライブラリだけでなく、大規模言語モデルの分散学習フレームワークであるMegatronLMが動作するかどうかの具体的な確認手順が紹介されています。

> **Zenn Llm** (https://zenn.dev/hiouchiy/articles/8d14adbdd416ba): Databricks Serverless GPU を使ってみる  ~MegatronLM編~
> 【翻訳】DatabricksがData + AI Summit 2025で発表した新機能「Serverless GPU」がベータ版として利用可能になりました。

## 9. 裁判資料で発覚OpenAI、初のAIデバイス開発に着手、市場投入は1年以上先か

- 裁判所の提出書類から、OpenAIが初のAIハードウェアデバイスを開発中であることが明らかになりました。しかし、製品の市場投入は1年以上先と見られており、開発はまだ初期段階にあることが示唆されています。

- 開発中のデバイスは、当初噂されたインイヤー型製品に限定されず、OpenAIは他の様々なフォームファクターも模索している模様です。これは、特定の形状に固執せず、幅広い可能性を検討していることを示しています。

- この情報は、OpenAIとデザイン会社io社との間の訴訟に関連する裁判資料によって判明しました。両社がAIデバイス開発の初期段階で協業していたことが示唆されており、この訴訟が開発の背景を明らかにする形となりました。

> **TechCrunch** (https://techcrunch.com/2025/06/23/court-filings-reveal-openai-and-ios-early-work-on-an-ai-device/): Court filings reveal OpenAI and io’s early work on an AI device
> 【翻訳】裁判所の提出書類から、OpenAIが初のAIハードウェアデバイスを開発中であることが明らかになりました。開発はまだ初期段階にあり、製品の市場投入は1年以上先になる見込みです。

## 10. テスラ、ロボタクシーの安全性に黄信号米NHTSAが交通違反で本格調査へ

- 米国運輸省道路交通安全局（NHTSA）が、テスラのロボタクシーサービスに関して同社に接触し、情報提供を求めていることが明らかになりました。これは規制当局による公式な調査の開始を示唆しています。

- この措置は、テキサス州サウスオースティンで運用されているテスラのロボタクシーが、交通法規に違反している様子を捉えた複数の動画がオンライン上で拡散したことを受けてのものです。

- 問題となっているロボタクシーサービスは、現在テスラが招待した一部の顧客のみを対象に提供されている限定的な試験運用段階にあり、今回の事案は本格展開に向けた安全性の課題を浮き彫りにしています。

> **TechCrunch** (https://techcrunch.com/2025/06/23/teslas-robotaxis-have-already-caught-the-attention-of-federal-safety-regulators/): Tesla’s robotaxis have already caught the attention of federal safety regulators
> 【翻訳】テスラのロボタクシーサービス計画に対し、米国の安全規制当局である運輸省道路交通安全局（NHTSA）が同社に接触し、情報提供を要請しました。これは、規制当局による公式な調査の開始を示唆する動きと見られています。

---

## Lawrence's Insights

*※ここにLawrenceさんの手入力コメントを追加してください*

---