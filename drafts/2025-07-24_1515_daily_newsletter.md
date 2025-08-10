# 2025年07月24日 AI NEWS TLDR

## GoogleによるAI・Geminiの最新動向

AI分野においてGoogleを含む複数の企業が新たな取り組みを発表しました。

今回は6件のAI関連ニュースをお届けします。

これらの動向は今後のAI技術の発展に大きな影響を与えることが予想されます。

## 目次

1. トランプ氏、日本車に15%関税！ボーイング100機購入で応酬、アジア貿易網に激震。

2. Google、Gemini Founders Forum開催！DeepMindとCloudがAIスタートアップを支援

3. LLMの推論能力向上を目指すRLVRにおいて、数学、コード生成

4. Ultra3D、3D生成を最大6.7倍高速化！高解像度1024でSOTA達成

5. はい、承知いたしました。プロのニュース見出し編集者として、記事要約から読者の関心を引く魅力的で具体的な日本語見出し...

6. ピーター・ティール「Facebookザッカーバーグは博識家、専門家でない起業家こそ成功

---

## 1. トランプ氏、日本車に15%関税！ボーイング100機購入で応酬、アジア貿易網に激震。

- トランプ氏は日本との間で、自動車を含む輸入品に15%の関税を課す取引を発表し、日本側はボーイング100機購入や米企業との防衛費増額で応じました。

- この関税措置は、フィリピンに対しては19%、インドネシアと同水準、ベトナムより低い20%未満の税率が適用される見通しです。

- ゴールドマン・サックスは、15%を新たな基準関税とし、銅や重要鉱物には50%の賦課を予測しており、今後の貿易政策への影響が注目されます。

- 関連して台湾も米国との新たな貿易交渉で合意を目指しており、地域経済への影響が広がる可能性があります。

> **Bay Area Times** (https://www.bayareatimes.com/p/trump-announces-japan-deal-with-15-tariffs-550b-fund-pledge): Trump announces Japan deal with 15% tariffs, $550B fund pledge
> トランプ氏、日本へ15%関税と5500億ドル基金約束で合意自動車産業への影響は避けられない。

---

## 2. Google、Gemini Founders Forum開催！DeepMindとCloudがAIスタートアップを支援

- Google for Startupsは、Google DeepMindとGoogle Cloudが共同で開催する「Gemini Founders Forum」への参加申し込み受付を開始しました。

- このフォーラムは、AI技術の最前線を探求するスタートアップ企業を対象とした2日間の対面式サミットとなります。

- 参加者は、GoogleのAI分野における最新動向や、Geminiモデルを活用した事業成長の機会について深く学ぶことができます。

> **Google Gemini Blog** (https://blog.google/outreach-initiatives/entrepreneurs/apply-google-for-startups-gemini-founders-fund/): Startups can apply now for the Google for Startups Gemini Founders Forum.
> Googleが提供する「Gemini Founders Forum」で、AIスタートアップが最新のGeminiモデルを活用し、プロダクト開発を加速させる絶好の機会。

---

## 3. LLMの推論能力向上を目指すRLVRにおいて、数学、コード生成

- LLMの推論能力向上を目指すRLVRにおいて、数学、コード生成、論理パズルといった複数ドメイン間の相互作用をGRPOアルゴリズムとQwen-2.5-7Bモデルを用いて分析し、単一ドメイン学習時の性能向上とドメイン間汎化能力を評価しています。

- 複数ドメインを組み合わせたクロスドメイン学習では、ドメイン間の相互強化や競合といった複雑な相互作用が生じることが実験により明らかになり、これらの影響を詳細に調査しています。

- ファインチューニング（SFT）が強化学習（RL）に与える影響を理解するため、ベースモデルとインストラクトモデルの性能差を同一RL設定下で比較分析し、学習戦略や報酬設計、言語要因の重要性も探求しています。

- 本研究は、LLMが現実世界の複雑な問題解決に必要な複数の認知スキルを統合的に活用できるよう、強化学習手法の最適化に向けた重要な知見を提供し、ドメイン間学習のダイナミクス解明に貢献します。

> **Huggingface Daily Papers** (https://arxiv.org/abs/2507.17512): Can One Domain Help Others? A Data-Centric Study on Multi-Domain Reasoning via Reinforcement Learning
> 強化学習によるマルチドメイン推論で、単一ドメインの知識が他ドメインの学習を加速させる可能性を、具体的なデータセットと学習曲線で実証。
> **Hacker News Ai** (https://blog.aridgwayweb.com/mcp-ollama-local-assistant-soon.html): Ollama and MCP – A blog about AI by AI, with help from me
> OllamaとMCPがAI開発を加速、AI自身がブログを執筆する未来への第一歩。

---

## 4. Ultra3D、3D生成を最大6.7倍高速化！高解像度1024でSOTA達成

- Ultra3Dは、3Dコンテンツ生成における計算効率の課題を解決するため、2段階拡散モデルの高速化を実現する革新的なフレームワークです。

- Part Attentionメカニズムは、幾何学的な構造を維持しつつ、局所的な注意計算に限定することで、潜在特徴の生成を最大6.7倍高速化します。

- 高解像度（1024解像度）での3D生成を可能にし、視覚的忠実度とユーザー評価の両面で最先端の性能を達成しています。

- スケーラブルなパートアノテーションパイプラインを構築し、メッシュデータをパートラベル付きの疎なボクセルに変換することで、Part Attentionの効率的な利用を可能にしています。

> **Huggingface Daily Papers** (https://arxiv.org/abs/2507.17745): Ultra3D: Efficient and High-Fidelity 3D Generation with Part Attention
> Ultra3Dは、**「部分アテンション」**という新技術で、**NVIDIA RTX 4090**でも数秒で**高精細な3Dモデル**を生成従来の手法を凌駕する**効率性と忠実度**を実現する。
---

## 5. はい、承知いたしました。プロのニュース見出し編集者として、記事要約から読者の関心を引く魅力的で具体的な日本語見出し...

- OllamaとMCP（Multi-Chat Protocol）の連携により、ローカル環境で複数の大規模言語モデル（LLM）を同時に活用できるAIアシスタントが実現しました。

- MCPは、ユーザーが複数のLLMと対話できるインターフェースを提供し、ローカルでのAIアシスタント利用体験を向上させます。

- 本技術は、AI自身がブログ記事を作成する試みの一環であり、AIでのコンテンツ生成の可能性を示唆しています。

- 関連技術として、部分アテンション機構を用いた高忠実度3D生成技術Ultra3Dも注目されており、AIの応用範囲の広がりを示しています。

> **Hacker News Ai** (https://blog.aridgwayweb.com/mcp-ollama-local-assistant-soon.html): Ollama and MCP – A blog about AI by AI, with help from me
> OllamaとMCPがAI開発を加速、AI自身がブログを執筆する未来への第一歩。
> **Huggingface Daily Papers** (https://arxiv.org/abs/2507.17745): Ultra3D: Efficient and High-Fidelity 3D Generation with Part Attention
> Ultra3D: Efficient and High-Fidelity 3D Generation with Part Attentionに関する参考記事

---

## 6. ピーター・ティール「Facebookザッカーバーグは博識家、専門家でない起業家こそ成功

- Peter Thiel氏は、世界クラスの起業家は専門家でなく、多様な分野に精通した博識家（polymaths）であると指摘しています。

- Mark Zuckerberg氏を例に挙げ、Facebookの製品詳細から社会心理学、文化動向、経営戦略、テクノロジー史まで幅広く深い理解を示す能力を挙げています。

- 学術界における狭い専門分野に特化する見解と対照的に、起業家に多岐にわたる知識を統合する知性が求められると述べています。

---

## Lawrence's Insights

*※ここにLawrenceさんの手入力コメントを追加してください*

---
