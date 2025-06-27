# 2025年06月26日 AI NEWS TLDR

## 研究・技術と企業・ビジネスの最新動向

Googleが2025年6月25日に発表。特に企業で広く使われるWindows環境での利便性向上が期待されますと発表しました。

Googleが、AIモデル「Gemini」をターミナルから直接利用できるオープンソースツール「Gemini CLI」を発表。Gemini CLIは、特に個人開発者向けに設計されており、強力なAIモデルへのアクセスを容易にしますと発表しました。

また、企業・ビジネス、Google・Gemini関連分野でも具体的な活用事例や技術進展が報告されています。

## 目次

1. Googleがしましたを発表

2. Infinitus SystemsがAIの提供を発表

3. 具体的な構築はDocker Composeを用いて行われます

4. OpenAIの研究成果発表

5. Raphe mPhibrがしましたを発表

6. 競合ツールがWSL（Windows Subsystem for Linux）を必要とする場合があるのに対し

7. Metaの最新動向

8. AI技術の最新発表

9. Microsoftの新技術開発

10. IBMの新技術開発

11. オンラインIDEを提供するReplit社のCEOは

12. AI技術の最新発表

---

## 1. Googleがしましたを発表

- Googleが、AIモデル「Gemini」をターミナルから直接利用できるオープンソースツール「Gemini CLI」を発表しました。これにより、開発者は慣れ親しんだコマンドライン環境を離れることなく、AIの機能をシームレスに活用できます。

- Gemini CLIは、特に個人開発者向けに設計されており、強力なAIモデルへのアクセスを容易にします。無料で利用できるオープンソースプロジェクトとして提供されるため、開発者は自由にカスタマイズや拡張を行うことが可能です。

- このツールの導入は、開発ワークフローの効率化を目的としています。コード生成やデバッグ支援といったタスクをターミナル上で完結させることができ、アプリケーション切り替えに伴う時間的ロスを削減します。

> **Google Gemini Blog** (https://blog.google/technology/developers/introducing-gemini-cli-open-source-ai-agent/): GoogleのAI「Gemini」をコマンドラインで直接使えるオープンソースツール「Gemini CLI」が公開。ターミナル上でコード生成やファイル内容の要約。
> **The Decoder** (https://the-decoder.com/google-releases-open-source-gemini-cli-to-bring-gemini-ai-into-developer-workflows/): Google。AIモデル「Gemini」をコマンドラインから直接操作できるオープンソースツール「Gemini CLI」を公開。開発者はターミナルを離れず。

## 2. Infinitus SystemsがAIの提供を発表

- Infinitus Systems社は、医療業界が直面する深刻な人材不足問題に対し、LLMとAI音声エージェントを活用したソリューションを提供しています。同社のCEOであるAnkit Jain氏がa16zのポッドキャストで語ったもので、反復的な管理業務の自動化を目指しています。

- 具体的には、保険給付資格の確認や事前承認といった、従来は人間が電話で行っていた時間のかかる業務をAIが代行します。これにより、医療スタッフは患者ケアなど、より専門性が高く価値のある業務に集中できるようになります。

- 同社はこれまでに500万件を超える患者中心の対話を自動化しており、その過程でAIの誤りを防ぐため、多層的なガードレール（安全機構）を設けることで、信頼性と安全性を確保するアプローチを取っています。

> **A16Z Youtube (YouTube)** (https://www.youtube.com/watch?v=A1elR8lofOo): Infinitus社CEOのAnkit Jain氏が提唱。会話型AIが保険会社への電話確認といった医療従事者の管理業務を自動化。煩雑な事務作業の時間を最大70%削減し。

## 3. 具体的な構築はDocker Composeを用いて行われます

- 本記事では、LLM実行フレームワーク「Ollama」とWeb UI「Open WebUI」を利用し、ローカルPC上に大規模言語モデルの実行環境を構築する手順を図解しています。Dockerを用いることで、複雑なセットアップを簡略化し、ChatGPTのような対話環境を構築します。

- 環境構築の前提として、NVIDIA製GPUを搭載したPCとDockerのセットアップが必要です。OllamaとOpen WebUIをそれぞれ別のDockerコンテナとして起動し、連携させることで、ブラウザ経由でLLMを操作するWebアプリケーション環境を実現します。

- 具体的な構築はDocker Composeを用いて行われます。`docker-compose.yml`ファイルに設定を記述しコマンドを実行するだけで、GPUを利用可能なOllamaとWeb UIの環境が一括で起動します。その後、Web UIから好みのLLMモデルをダウンロードして利用を開始できます。

- この手法の利点は、ローカル環境で完結するため、API料金や機密情報の漏洩リスクを懸念することなくLLMを利用できる点です。Dockerによる環境構築の容易さも特徴で、開発者が手軽に生成AIを試すことが可能になります。

> **Zenn Llm** (https://zenn.dev/stockdatalab/articles/20250626_tech_env_llm): Docker上でOllamaとOpen WebUIを連携させ。Llama 3やMistral等のオープンソースLLMをローカルPCで実行。API料金不要。

## 4. OpenAIの研究成果発表

- Meta社が、OpenAIのチューリッヒオフィスを設立した主要研究者であるLucas Beyer氏、Alexander Kolesnikov氏、Xiaohua Zhai氏の3名を引き抜いたと報じられました。これはAI分野におけるトップ人材獲得競争の激化を象徴する出来事です。

- 今回の引き抜きは、Metaのマーク・ザッカーバーグCEOが主導する大規模な採用活動の一環です。競合であるOpenAIのサム・アルトマンCEOがザッカーバーグ氏の採用手法を公に揶揄する中での成功となり、注目を集めています。

- 移籍した3名の研究者は、Metaのスーパーインテリジェンス部門に加わります。これにより、Metaは汎用人工知能（AGI）開発に向けた研究開発体制をさらに強化し、OpenAIなどとの競争で優位に立つことを目指しています。

> **TechCrunch** (https://techcrunch.com/2025/06/25/metas-recruiting-blitz-claims-three-openai-researchers/): MetaがOpenAIの研究者3名を獲得。これはAI研究部門FAIRを強化し。次世代LLM「Llama 3」の開発を加速させる狙いか。トップ研究者を巡る数億円規模の報酬での引き抜き合戦が。

## 5. Raphe mPhibrがしましたを発表

- インドのドローンスタートアップであるRaphe mPhibr社が、1億ドルの資金調達を実施したことを発表しました。この背景には、近年の地政学的状況を反映した軍事用UAV（無人航空機）への需要が世界的に急増していることがあります。

- 調達した資金は、主に研究開発（R&D）能力の強化と、インド国内における生産体制の増強に充当される計画です。これにより、最先端のドローン技術を自社開発し、国内需要に迅速に対応する体制を構築することを目指します。

- 今回の資金調達は、特に戦場での実用や国境警備といった防衛分野でのドローン需要が急激に高まっている状況を反映しています。同社の技術は、インドの防衛および監視能力の近代化に大きく貢献することが期待されています。

> **TechCrunch** (https://techcrunch.com/2025/06/25/indian-drone-startup-raphe-mphibr-raises-100m-as-military-uav-demand-soars/): インドのドローン企業Raphe mPhibrが1億ドルを調達。中国との国境紛争で軍事用UAVの需要が急増する中。政府の「Make in India」政策を追い風に。

## 6. 競合ツールがWSL（Windows Subsystem for Linux）を必要とする場合があるのに対し

- Googleが2025年6月25日に発表した新しい開発者ツール「Gemini CLI」は、Windows環境にネイティブ対応している点が大きな特徴です。これにより、多くのWindowsユーザーがWSLなしで直接利用可能となります。

- 競合ツールがWSL（Windows Subsystem for Linux）を必要とする場合があるのに対し、Gemini CLIはWindowsに直接対応することで導入のハードルを下げました。特に企業で広く使われるWindows環境での利便性向上が期待されます。

- 導入は非常に簡単で、ターミナル上で`npx https://github.com/Google-gemini/gemini-cli`という単一のコマンドを実行するだけで利用を開始できます。この手軽さが、開発者による迅速な試用と普及を後押しすると見られています。

> **Zenn Llm** (https://zenn.dev/acntechjp/articles/4e601d6379255b): GoogleのGemini CLIは。検索エンジンをコマンドラインに統合した次世代ツール。ファイル操作やパイプラインと連携し。自然言語で直接コード生成やデータ分析を実行。

## 7. Metaの最新動向

- コメディアンのサラ・シルバーマン氏ら13人の著者が、自著をAIの学習に不正利用されたとしてMeta社を訴えた著作権侵害訴訟で、米連邦裁判所はMeta社側の主張を認める判決を下しました。

- 裁判所は、原告側がMeta社のAIモデル「Llama」の学習データセットに、彼らの著作物が実際に含まれていたことを示す直接的な証拠を提示できなかったことを、判決の主な理由として挙げています。

- Llamaが作品の要約を生成できるという原告の主張に対し、裁判所は、それはウェブ上の書評などから学習した結果の可能性があり、著作物を直接コピーした証拠にはならないと判断しました。

> **TechCrunch** (https://techcrunch.com/2025/06/25/federal-judge-sides-with-meta-in-lawsuit-over-training-ai-models-on-copyrighted-books/): MetaのAI「Llama」が著作権書籍を学習データに利用した訴訟で。連邦地裁がMetaを支持。作家サラ・シルバーマンらの訴えに対し。
> **VentureBeat AI** (https://venturebeat.com/ai/boston-consulting-group-to-unlock-enterprise-ai-value-start-with-the-data-youve-been-ignoring/): BCGが指摘。企業のAI価値創出は。売上データではなく。これまで無視されてきた議事録やメール等の「ダークデータ」の活用が鍵。生成AIでこの90%とも言われる未活用データを分析し。
> **Semianalysis** (https://semianalysis.com/2025/06/25/ai-training-load-fluctuations-at-gigawatt-scale-risk-of-power-grid-blackout/): 次世代LLMのトレーニングが引き起こす、ギガワット級の急激な電力負荷変動。この予測不能な需要スパイクは電力網の安定性を脅かし、データセンター集積地で大規模停電を引き起こす現実的リスクに。

## 8. AI技術の最新発表

- ECプラットフォーム「カウシェ」は、「圧倒的速度で技術を事業価値に転換する」という目標を掲げ、バックエンド開発領域でLLM活用を本格的に推進しました。開発の初期段階からLLMを前提に据え、生産性の飛躍的な向上を目指しています。

- LLMの性能を最大限に引き出すため、一貫した命名規則やディレクトリ構造、シンプルな設計、TypeScriptによる厳密な型定義などを徹底しました。これにより、LLMがコードの文脈を理解しやすく、精度の高い提案を生成できる基盤を構築しています。

- この取り組みの結果、GitHub Copilotのコード提案採用率が、全社平均の30%を大幅に上回る40%を記録しました。これは、LLMフレンドリーなコードベースが、AIによる開発支援の質を具体的に向上させたことを示す客観的な指標となります。

- カウシェの事例は、コードベースの品質と一貫性を意図的に高めることが、AI開発支援ツールの効果を最大化する鍵であることを示しています。これにより、開発者の生産性向上だけでなく、事業価値創出の加速にも直接貢献できることが実証されました。

> **Zenn Llm** (https://zenn.dev/kauche/articles/989cf9e2f38fa6): カウシェがGoバックエンドで実践するLLMフレンドリー設計。GitHub Copilotの精度を最大化するため。型定義の徹底と単一責任の原則を遵守。これにより開発リードタイムを25%短縮し。

## 9. Microsoftの新技術開発

- Microsoftのサティア・ナデラCEOは、AIをPCやインターネットに続く根本的なプラットフォームシフトと位置づけ、フロンティアモデルを訓練するための大規模インフラ構築に全社的に取り組んでいると語りました。

- AIのハイパースケール化に伴うエネルギー消費の課題に言及し、技術革新だけでなく、計算資源を利用するための社会的な合意形成や責任ある運用が不可欠であるとの見解を示しました。

- 次世代アプリケーションは、Copilotのようにユーザーの意図を予測し自律的にタスクを実行する「推論能力」が中核になると指摘。既存アプリの単なる機能拡張ではない、根本的な再設計が必要になるとの未来像を語りました。

- AIの進化と並行し、Microsoftが量子コンピューティング分野でもブレークスルーを目指していることを明かしました。将来的には、量子コンピュータがAIモデルの性能を飛躍的に向上させる重要な鍵になるとの展望を示しています。

> **Ycombinator Youtube (YouTube)** (https://www.youtube.com/watch?v=AUUZuzVHKdo): Microsoft。OpenAIとの提携でCopilotを全製品に統合。Azureのハイパースケールインフラを自社製AIチップで強化し。

## 10. IBMの新技術開発

- IBMの観察によると、現代の企業は単一のAIモデルに依存せず、オープンソース、商用、自社開発の小規模モデルを組み合わせる「マルチモデル戦略」を積極的に採用しています。これは、特定の業務要件やコスト効率に応じて最適なモデルを選択する必要性が高まっているためです。

- マルチモデル環境における最大の課題は、要約、コード生成、顧客対応といった多様なユースケースに対し、どのLLMが最適かを判断することです。企業はコスト、性能、精度、データプライバシーなどの複数要素を考慮し、最適なモデルを戦略的に選択する必要に迫られています。

- この課題に対しIBMは、エンタープライズAIプラットフォーム「watsonx」をソリューションとして提供しています。このプラットフォームは、多様なAIモデルを一元的に管理・統制し、開発者が各ユースケースに最適なモデルを容易に選択・活用できる環境を構築します。

> **VentureBeat AI** (https://venturebeat.com/ai/ibm-sees-enterprise-customers-are-using-everything-when-it-comes-to-ai-the-challenge-is-matching-the-llm-to-the-right-use-case/): IBMの見解では。企業はGPT-4やLlama 3など複数AIを無秩序に導入。今後は。watsonx等を活用し。顧客対応やデータ分析といったユースケース毎に。
> **VentureBeat AI** (https://venturebeat.com/ai/boston-consulting-group-to-unlock-enterprise-ai-value-start-with-the-data-youve-been-ignoring/): Boston Consulting Groupの指摘。企業のAI価値創出の鍵は。これまで無視されてきた「ダークデータ」。コールセンターの音声や社内文書を生成AIで分析し。

## 11. オンラインIDEを提供するReplit社のCEOは

- オンラインIDEを提供するReplit社のCEOは、ソフトウェア開発の未来が「agents all the way down」、つまり開発の全工程をAIエージェントが担う世界になるとのビジョンを提唱しています。

- 同社のAIエージェントは、プログラミング経験のない非開発者でも、わずか15分という短時間でアプリケーションの設計からコーディングまでを完了させる能力を実証しました。

- この技術は、自然言語による曖昧な指示からコードを生成する「vibe coding」という概念を具現化し、専門知識の壁を取り払うことでソフトウェア開発のあり方を根本から変える可能性を秘めています。

> **VentureBeat AI** (https://venturebeat.com/ai/for-replits-ceo-the-future-of-software-is-agents-all-the-way-down/): Replit社CEOが提唱する「agents all the way down」構想。自然言語の指示に基づき。複数のAIエージェントが協調してソフトウェアを自律的に開発・保守。

## 12. AI技術の最新発表

- ボストン・コンサルティング・グループ（BCG）は、企業がAIの価値を最大限に引き出す鍵は、これまで無視されてきた非構造化データにあると指摘しています。企業の保有するデータの80%以上を占めるこれらのデータを活用することが、実験段階を超えたAIの本格導入に不可欠です。

- 生成AI、特に大規模言語モデル（LLM）の登場により、テキスト、画像、音声といった非構造化データの解析が飛躍的に容易になりました。これにより、顧客からのフィードバック、契約書、社内文書などから新たな洞察を得て、業務効率化やリスク管理に繋げることが可能になります。

- BCGは、AI導入の成功には単なるツール導入だけでなく、自社が保有する非構造化データを特定し、活用戦略を策定することが重要だと強調しています。データ基盤の整備やガバナンス体制の構築、従業員のスキル育成が成功の前提条件となります。

> **VentureBeat AI** (https://venturebeat.com/ai/boston-consulting-group-to-unlock-enterprise-ai-value-start-with-the-data-youve-been-ignoring/): BCGが提言。企業のAI価値創出の鍵は。コールセンターの音声ログや顧客メールといった「ダークデータ」の活用にある。企業の8割が未着手なこの領域にこそ。
> **TechCrunch** (https://techcrunch.com/2025/06/25/federal-judge-sides-with-meta-in-lawsuit-over-training-ai-models-on-copyrighted-books/): 連邦裁判所。メタ社のAI「Llama」が著作権書籍を学習データに利用した訴訟で同社を支持。作家サラ・シルバーマンらの訴えを退け。AI学習は「フェアユース」に該当するとの判断。
> **VentureBeat AI** (https://venturebeat.com/ai/ibm-sees-enterprise-customers-are-using-everything-when-it-comes-to-ai-the-challenge-is-matching-the-llm-to-the-right-use-case/): IBMの分析。企業はOpenAIのGPT。MetaのLlama。Mistralなど複数LLMを併用し。特定ベンダーに依存しない傾向。真の課題は。顧客対応やコード生成といった業務ごとに。

---

## Lawrence's Insights

*※ここにLawrenceさんの手入力コメントを追加してください*

---
