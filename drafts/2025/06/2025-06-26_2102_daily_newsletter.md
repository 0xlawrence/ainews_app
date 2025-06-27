# 2025年06月26日 AI NEWS TLDR

## 研究・技術とOpenAI・GPT関連の最新動向

ChatGPTが。ローカルLLM環境の構築には、OllamaとOpen WebUIという主要ツールが活用されますと発表しました。

大規模言語モデル（LLM）分野では複数の重要な技術進展が報告され、実用化に向けた動きが加速しています。

企業におけるAI活用が本格化し、具体的な業務改善や新サービス創出の事例が相次いで発表されています。

## 目次

1. Metaの新技術開発

2. OpenAIの最新動向

3. Infinitus Systems, Inc.のCEO兼共同創業者であるAnkit Jain氏は

4. 【図解】OllamaとOpen WebUI…関連ニュース

5. OpenAIの研究成果発表

---

## 1. Metaの新技術開発

- 米国カリフォルニア州の連邦裁判所は、Meta社が大規模言語モデル「Llama」の訓練に著作権保護された書籍を使用したことに関する高名な訴訟で、Meta社に有利な判決を下しました。この判決は、AI開発における著作権利用の法的枠組みに注目が集まる中で出されました。

- しかし、今回の判決はAI企業が著作権保護された作品を自由に利用できる「白紙委任」を与えるものではないと、裁判官は明確に警告しています。これは、AIモデルの訓練データとしての著作物利用に関する法的解釈が依然として流動的であることを示唆しています。

- 裁判官は、将来の類似訴訟においては異なる判決が下される可能性もあると指摘しており、AI技術の進化に伴う著作権法の適用について、今後の司法判断が慎重に進められる見込みです。AI開発企業は、引き続き著作権侵害のリスクを考慮する必要があります。

> **The Decoder** (https://the-decoder.com/meta-wins-over-llama-book-training-but-the-judge-warns-future-cases-could-go-differently/): MetaがLlamaの大規模言語モデル学習における書籍データ利用で著作権侵害訴訟に勝訴。しかし。裁判官は今後のAI学習データに関する著作権訴訟で異なる判決の可能性を示唆し。

## 2. OpenAIの最新動向

- OpenAIが営利企業への転換を目指す中で、Microsoftとの契約再交渉が進められており、特にAGI（汎用人工知能）マイルストーン達成時にMicrosoftのアクセスを制限できるという既存の条項を巡り、両社間で激しい対立が生じています。過去2週間で、両社は過激な行動を示唆するほど緊張が高まっていると報じられています。

- OpenAIの幹部らは過去8ヶ月にわたり、AGIが間もなく宣言される可能性を示唆してきました。これに対し、Microsoftは現在の交渉で、AGIに関する条項の撤廃、またはOpenAIの知的財産（IP）への独占的アクセス確保を目指していると報じられています。これは、将来的なAI技術の主導権と利用権を巡る重要な争点です。

- OpenAIは営利企業への転換を通じて、より柔軟な事業展開と収益化を目指していると考えられます。一方、MicrosoftはOpenAIへの巨額投資と戦略的提携でAI分野の優位性を確立しており、AGIの定義やアクセス権がその戦略に不可欠と認識しています。この対立は、AI業界におけるパートナーシップの複雑さを示しています。

> **Bay Area Times** (https://www.bayareatimes.com/p/microsoft-openai-said-to-clash-over-definition-of-agi): MicrosoftとOpenAIがAGIの「人間レベルの汎用性」と「自律的な進化能力」の定義で対立。これは。MicrosoftのCopilot統合戦略と。

## 3. Infinitus Systems, Inc.のCEO兼共同創業者であるAnkit Jain氏は

- Infinitus Systems, Inc.のCEO兼共同創業者であるAnkit Jain氏は、ヘルスケア分野の深刻な人材不足に対し、LLMとAI音声エージェントを活用したソリューションを提供していると述べました。同社の技術は、給付金確認や事前承認といった反復的な業務を自動化し、医療従事者がより専門的で高価値な業務に集中できる環境を創出しています。

- Infinitus Systems, Inc.は、初期の概念実証段階から飛躍的に成長し、これまでに500万件を超える患者中心のインタラクションを処理する実績を上げています。この大規模な自動化により、医療機関は限られた人的資源を最適に配置し、患者ケアの質の向上に貢献している点が強調されました。

- AI活用における潜在的なエラーリスクに対し、Infinitus Systems, Inc.は多層的なガードレールを設けることでその軽減を図っています。Ankit Jain氏は、この堅牢なアプローチが、自動化されたプロセスにおける信頼性と正確性を確保し、ヘルスケア分野でのAI導入を安全に進める上で不可欠であると説明しました。

> **A16Z Youtube (YouTube)** (https://www.youtube.com/watch?v=A1elR8lofOo): Ankit Jainが。AIと高度なデータ分析を駆使し。医療現場の看護師・医師の過重労働を解消。患者データから最適な人員配置を予測し。事務作業を自動化することで。

## 4. 【図解】OllamaとOpen WebUI…関連ニュース

- ChatGPTなどの生成AIが普及する中、専門知識がなくてもローカル環境で大規模言語モデル（LLM）を動かしたいというニーズが高まっています。本記事は、この課題に対応するため、OllamaとOpen WebUIを活用した具体的な環境構築手順を解説しています。

- ローカルLLM環境の構築には、OllamaとOpen WebUIという主要ツールが活用されます。これらをDockerコンテナとして連携させることで、ユーザーは手軽に自身のPC上でLLMを運用できるブラウザベースのインターフェースを実現します。

- 具体的な構築方法として、2つのDockerコンテナを連携させ、ブラウザからプロンプトを入力できる環境を構築します。このシステムは、NVIDIA製GPUを搭載したPCでの動作を前提としており、高性能なローカルLLMの利用を可能にします。

> **Zenn Llm** (https://zenn.dev/stockdatalab/articles/20250626_tech_env_llm): OllamaとOpen WebUIをDockerで連携させ。手元のPCで大規模言語モデルを動かす具体的な環境構築手順。クラウド依存を避け。

## 5. OpenAIの研究成果発表

- Meta社がOpenAIから3名の主要AI研究者を引き抜いたと報じられました。これは、AI分野におけるトップ人材獲得競争が激化する中で、MetaがOpenAIのSam Altman氏による採用戦略への批判にもかかわらず、重要な勝利を収めたことを示しています。

- 引き抜かれた研究者は、OpenAIのチューリッヒオフィスを設立したLucas Beyer氏、Alexander Kolesnikov氏、Xiaohua Zhai氏の3名です。彼らはMetaの「superintelligence」部門に加わったとされており、MetaのAI開発能力強化に貢献することが期待されます。

- OpenAIのCEOであるSam Altman氏は、MetaのCEOであるMark Zuckerberg氏の積極的な採用戦略を公に批判していましたが、今回の引き抜きは、MetaがAI研究開発における人材確保において、その批判を乗り越え、引き続き強力な攻勢をかけている現状を浮き彫りにしています。

> **TechCrunch** (https://techcrunch.com/2025/06/25/metas-recruiting-blitz-claims-three-openai-researchers/): MetaがOpenAIからAI研究者3名を電撃引き抜き。生成AI開発競争が激化。ChatGPTを開発したOpenAIのコア人材流出は。MetaのLlamaや次世代AIモデル開発を加速させ。

---

## Lawrence's Insights

*※ここにLawrenceさんの手入力コメントを追加してください*

---
