# 2025年06月24日 AI NEWS TLDR

## AI人材需要6倍増、Googleの新検索とDatabricksのServerless GPU発表

ビジネスSNSのLinkedInによると、AI関連求人は過去1年で6倍に増え、人材獲得競争が激化しています。

この動きを背景に、Googleは対話型AI検索「AI mode」をインドで試験導入するなど、新サービスの展開を加速。

さらにDatabricksはNVIDIA A10搭載の「Serverless GPU」を発表し、開発環境の革新も進んでいます。

## 目次

1. LinkedIn調査：AI求人6倍増に対し、個人のスキル追加は20倍に人材市場が沸騰

2. Googleの次世代AI検索「AI mode」、巨大市場インドで先行テストを開始

3. Databricksの新機能「Serverless GPU」ベータ

4. のClaude Code拡張機能に深刻な脆弱性

5. 数時間のシステム障害分析をわずか2分に短縮し

6. OpenAIの次の一手はAIハードウェア！裁判資料で開発が判明、投入は1年以上先

7. テスラのロボタクシー、交通違反で米NHTSAが調査開始本格展開に早くも暗雲

8. MIT、AIが自ら学び続ける新フレームワーク「SEAL」を発表静的モデルの限界を突破

9. AIの可観測性とMCPサポートでセキュアな運用を実現

---

## 1. LinkedIn調査：AI求人6倍増に対し、個人のスキル追加は20倍に人材市場が沸騰

- ビジネスSNSのLinkedInによると、AIに言及する求人情報が過去1年間で6倍に増加したことが、同社のCEOであるRyan Roslansky氏によって明らかにされました。これは、様々な業界でAI技術の導入が進み、関連する専門知識を持つ人材への需要が急激に高まっていることを示しています。

- 求人市場の需要増と並行して、LinkedInユーザーが自身のプロフィールにAI関連スキルを追加する動きは過去1年で20倍にも急増しました。これは、労働者が市場価値を高めるため、生成AIなどの新しい技術を積極的に学習し、キャリアに活かそうとする意識の表れです。

- 求人数の6倍増とスキル追加の20倍増というデータは、AIが労働市場の需要と供給の両面に劇的な変化をもたらしていることを浮き彫りにします。企業は即戦力を求め、個人はスキルアップで応えるという、AI時代におけるキャリア形成の新しい潮流を示唆しています。

> **The Decoder** (https://the-decoder.com/ai-job-postings-on-linkedin-grew-sixfold-as-ai-skill-additions-to-profiles-soared-twentyfold/): AI job postings on LinkedIn grew sixfold as AI skill additions to profiles soared twentyfold
> 【翻訳】ビジネスSNSのLinkedInによると、AI関連の求人情報が過去1年で6倍に増加しました。一方、プロフィールにAIスキルを追加する動きは20倍に達しており、AI技術を持つ人材への需要が業界全体で急激に高まっています。

> **The Decoder** (https://the-decoder.com/ai-job-postings-on-linkedin-grew-sixfold-as-ai-skill-additions-to-profiles-soared-twentyfold/)

> **Stratechery** (https://stratechery.com/2025/checking-in-on-ai-and-the-big-five/?access_token=eyJhbGciOiJSUzI1NiIsImtpZCI6InN0cmF0ZWNoZXJ5LnBhc3Nwb3J0Lm9ubGluZSIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJzdHJhdGVjaGVyeS5wYXNzcG9ydC5vbmxpbmUiLCJhenAiOiJIS0xjUzREd1Nod1AyWURLYmZQV00xIiwiZW50Ijp7InVyaSI6WyJodHRwczovL3N0cmF0ZWNoZXJ5LmNvbS8yMDI1L2NoZWNraW5nLWluLW9uLWFpLWFuZC10aGUtYmlnLWZpdmUvIl19LCJleHAiOjE3NTMzMDc1MTEsImlhdCI6MTc1MDcxNTUxMSwiaXNzIjoiaHR0cHM6Ly9hcHAucGFzc3BvcnQub25saW5lL29hdXRoIiwic2NvcGUiOiJmZWVkOnJlYWQgYXJ0aWNsZTpyZWFkIGFzc2V0OnJlYWQgY2F0ZWdvcnk6cmVhZCBlbnRpdGxlbWVudHMgcG9kY2FzdCByc3MiLCJzdWIiOiIwMTk0YWE3NS05MzVhLTc1MGUtYTE3Mi1kNTVjMDkwZGY0MDAiLCJ1c2UiOiJhY2Nlc3MifQ.Wm2VIepj9qaKUp0Vlmp--gW0oa6ojY15XxCEJvjtS-ivGUXvP9DOqaFTkhzgbzFK9hL8h_iJtsoD38AsQzh0nQn2C1JIhq4f1E2YfKgaxSzRWMsJnyrroXEI_k4e5gsXCkKZm1dJcLSpkJFH7hqBc42dV43dw_gQL-Nrdh_LXVodUEPDbpPwvinfIQ1NoRayljcS9VEZZ2j4_8UDKIABXKCvhBLxzy6fXsfc4CQL_M4VvtHlSGta2sceTJUo8CVyKxABeaqU9DfmkWVpVjBhoRiXJWzy_slD0OCBTzmzw318gLiD_MNcIHr2uwIIllgDBpHa9WQRdKBj_WBsV6QZoQ)

## 2. Googleの次世代AI検索「AI mode」、巨大市場インドで先行テストを開始

- Googleは、Q&A形式のAI検索ツール「AI mode」をインド市場で提供開始しました。この機能はまだ実験段階にあり、ユーザーはGoogleの実験的機能プラットフォームである「Search Labs」を通じてオプトインすることで利用可能になります。

- この新しいAIモードは、ユーザーが質問を投げかけると対話形式で回答を生成する検索ツールです。提供開始時点では英語でのクエリにのみ対応しており、他の言語へのサポート拡大については現段階では明言されていません。

- 今回のインドでの導入は、Googleが生成AIを検索体験に統合する世界的な取り組みの一環です。巨大なユーザーベースを持つインド市場で実験的に提供することで、今後の機能改善やグローバル展開に活かす戦略的な意図があります。

> **TechCrunch** (https://techcrunch.com/2025/06/23/google-introduces-ai-mode-to-users-in-india/): Google introduces AI mode to users in India
> 【翻訳】Googleは、Q&A形式のAI検索ツール「AI mode」をインド市場で提供開始しました。この機能はまだ実験段階にあり、Googleの実験的機能プラットフォーム「Search Labs」を通じてオプトインすることで利用可能になります。

> **TechCrunch** (https://techcrunch.com/2025/06/23/google-introduces-ai-mode-to-users-in-india/)

> **Google Blog** (https://blog.google/technology/ai/ask-a-techspert-what-is-inference/)

## 3. Databricksの新機能「Serverless GPU」ベータ

- Databricksは、Data + AI Summit 2025で新機能「Serverless GPU」を発表しました。本機能は現在ベータ版として提供されており、ユーザーはオンデマンドで単一のNVIDIA A10 GPUをノートブック環境で利用することが可能です。

- 将来的には、より高性能なNVIDIA H100 GPUによるマルチGPU構成への拡張が計画されており、大規模なAIモデルのトレーニングや推論におけるスケーラビリティ向上が期待されます。

- 記事では、この新しいServerless GPU環境上で、大規模言語モデルの学習フレームワークである「MegatronLM」が正常に動作するかを具体的に検証しており、その互換性を確認する試みが紹介されています。

> **Zenn Llm** (https://zenn.dev/hiouchiy/articles/8d14adbdd416ba): Databricks Serverless GPU を使ってみる  ~MegatronLM編~
> 【翻訳】AI関連の注目すべき最新ニュースの詳細報告

## 4. AnthropicのClaude Code拡張機能に深刻な脆弱性、VSCodeからファイルが読み取られる危険即時

- Anthropic社のAIコーディングアシスタント「Claude Code」のIDE拡張機能において、深刻なセキュリティ脆弱性が発見されました。この問題はWebSocket接続が任意のオリジンからの接続を許可してしまうもので、開発者には即時のアップデートが強く推奨されています。

- この脆弱性を悪用されると、ユーザーが悪意のあるWebサイトを訪問するだけで、攻撃者がIDEに不正アクセスする可能性があります。これにより、ローカルファイルの読み取り、開発作業の監視、さらには限定的なコード実行といった深刻な被害につながる恐れがあります。

- 影響を受けるのは、VSCode、Cursor、Windsurf、VSCodiumといった主要なVSCode系IDEで利用されている「Claude Code for VSCode」拡張機能の脆弱性バージョンです。利用者は自身の拡張機能のバージョンを確認し、速やかに最新版へ更新する必要があります。

> **Zenn Llm** (https://zenn.dev/kimkiyong/articles/c60cab6dcb0260): Claude Code IDE拡張機能の重要なセキュリティ脆弱性 - 即座にアップデート推奨

## 5. Traversal社のAI、数時間のシステム障害分析をわずか2分に短縮し、DevOpsの根本原因特定を自動化

- スタートアップ企業のTraversal社は、システム障害の根本原因分析（RCA）を劇的に高速化するAIエージェントを開発しました。因果推論の学術研究を応用し、従来エンジニアチームが数時間かけていた分析作業をわずか2〜4分に短縮します。

- 同社のAIエージェントは、複雑なシステムの依存関係マップを体系的に探索し、問題を引き起こしているログやコードの変更箇所を特定します。これにより、DevOpsやSREチームの障害対応における負担を大幅に軽減することを目指しています。

- AIによるコード生成が普及する中、人間が直接記述していないコードのデバッグという新たな課題が浮上しています。Traversalのソリューションは、このようなAI生成システムのトラブルシューティングを自動化し、大規模ソフトウェアの信頼性維持に貢献します。

> **Sequoia Youtube** (https://www.youtube.com/watch?v=7hBG5ShQ2BA): From DevOps ‘Heart Attacks’ to AI-Powered Diagnostics With Traversal’s AI Agents
> 【翻訳】スタートアップのTraversal社は、因果推論を応用したAIエージェントを開発しました。「DevOpsの心臓発作」とも呼ばれる突発的なシステム障害に対し、従来数時間かかっていた根本原因分析をわずか2〜4分に短縮します。

> **YouTube** (https://www.youtube.com/watch?v=7hBG5ShQ2BA)

> **VentureBeat** (https://venturebeat.com/ai/salesforce-launches-agentforce-3-with-ai-agent-observability-and-mcp-support/)

## 6. OpenAIの次の一手はAIハードウェア！裁判資料で開発が判明、投入は1年以上先

- OpenAIが独自のAIハードウェアデバイスを開発中であることが、裁判所に提出された書類によって明らかになりました。これは、同社がソフトウェアサービスに加え、物理的な製品市場への参入を初期段階から検討していることを示す動きです。

- 開発はまだ初期段階にあり、最初のハードウェアデバイスが市場に投入されるまでには1年以上かかると見られています。このタイムラインは、製品化に向けた技術開発や設計にまだ多くの時間を要することを示唆しています。

- デバイスの具体的な形状（フォームファクター）はまだ確定していません。訴訟での言及によると、インイヤー型（耳装着型）だけでなく、他の様々な形状の可能性も探っており、多様なユースケースを想定していると考えられます。

> **TechCrunch** (https://techcrunch.com/2025/06/23/court-filings-reveal-openai-and-ios-early-work-on-an-ai-device/): Court filings reveal OpenAI and io’s early work on an AI device
> 【翻訳】OpenAIが独自のAIハードウェアデバイスを開発していることが、裁判所に提出された書類によって明らかになりました。この動きは、同社がソフトウェアサービスに加え、物理的な製品市場への参入を初期段階から検討していたことを示しています。

## 7. テスラのロボタクシー、交通違反で米NHTSAが調査開始本格展開に早くも暗雲

- 米国運輸省道路交通安全局（NHTSA）が、テスラのロボタクシーに関して同社に接触しました。これは、オンライン上に投稿された複数の動画で、同社の車両が交通法規に違反している様子が確認されたことを受けた措置です。

- 問題となっているロボタクシーは、テキサス州サウスオースティンで招待された顧客向けに限定的に提供されているサービスです。この地域での運用中に、交通法規を無視するような挙動が複数報告されています。

- このNHTSAによる迅速な接触は、自動運転技術、特に一般市民を乗せるロボタクシーサービスに対する連邦安全規制当局の厳しい監視体制を浮き彫りにするものです。サービスの本格展開を前に、安全性の証明が急務となります。

> **TechCrunch** (https://techcrunch.com/2025/06/23/teslas-robotaxis-have-already-caught-the-attention-of-federal-safety-regulators/): Tesla’s robotaxis have already caught the attention of federal safety regulators
> 【翻訳】テスラのロボタクシーが早くも米国の安全規制当局の注目を集めています。オンライン上で交通法規に違反する動画が確認されたことを受け、NHTSA（米国運輸省道路交通安全局）が同社に接触しました。

## 8. MIT、AIが自ら学び続ける新フレームワーク「SEAL」を発表静的モデルの限界を突破

- マサチューセッツ工科大学（MIT）の研究者が、言語モデルが継続的に自己学習できる新フレームワーク「SEAL」を開発しました。従来の静的なAIモデルと異なり、一度トレーニングされた後も新しい知識やタスクを自律的に習得できる点が特徴です。

- このSEALフレームワークは、AIモデルが訓練後に新しい情報を学ぶのが困難という「継続的学習」の課題解決を目指しています。これにより、モデルは常に最新情報を反映し、変化する環境へ柔軟に適応し続ける能力の獲得が期待されます。

- SEALは「言語を通じた自己改善型具現化エージェント」として、環境との相互作用から学習する仕組みを持ちます。この動的な学習能力は、AIがより自律的で汎用性の高い存在へと進化する上で重要な技術的進歩と言えます。

> **Venturebeat Ai** (https://venturebeat.com/ai/beyond-static-ai-mits-new-framework-lets-models-teach-themselves/): Beyond static AI: MIT’s new framework lets models teach themselves
> 【翻訳】マサチューセッツ工科大学（MIT）が、言語モデルが自己学習を続ける新フレームワーク「SEAL」を開発しました。従来の静的なAIと異なり、一度訓練された後も新しい知識やタスクを自律的に習得し続ける点が画期的です。

## 9. Salesforce「Agentforce 3」発表AIの可観測性とMCPサポートでセキュアな運用を実現

- Salesforce社が、新製品「Agentforce 3」を発表しました。この製品は、AIエージェントのオブザーバビリティ（可観測性）とMCP（Model Connector Protocol）のネイティブサポートを主要な特徴としています。

- AIエージェントのオブザーバビリティ機能により、企業はAIの動作状況やパフォーマンスをリアルタイムで詳細に可視化・監視できるようになり、迅速な問題解決と運用効率の向上が可能になります。

- MCPをネイティブでサポートすることで、異なるAIモデルやシステム間での安全な相互運用性が確保されます。これにより、多様なツールを組み合わせたセキュアなAIエコシステムの構築が促進されます。

> **Venturebeat Ai** (https://venturebeat.com/ai/salesforce-launches-agentforce-3-with-ai-agent-observability-and-mcp-support/): Salesforce launches Agentforce 3 with AI agent observability and MCP support
> 【翻訳】SalesforceのAgentに関する最新技術発表について詳細解説

---

## Lawrence's Insights

*※ここにLawrenceさんの手入力コメントを追加してください*

---