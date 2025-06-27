# 2025年06月23日 AI NEWS TLDR

## AIの攻防とCornelis社の新技術「…

犯罪用AI「WormGPT」が「Grok」を悪用して進化し、サイバー攻撃の脅威を拡大させています。

一方、ChatGPT開発を率いたPeter Deng氏のように、数十億人規模の製品構築を成功させたキーパーソンの知見も注目されます。

その裏ではCornelis社が通信速度6倍の「CN500」を発表し、LLM開発のインフラを支えています。

それでは各トピックの詳細を見ていきましょう。

## 目次

1. サイバー犯罪者が、フィッシングメール作成などに悪用されるAIツール「WormGPT」を、よ…

2. OpenAI、Instagram、Uberなどで製品開発を率いたPeter Deng氏が、…

3. Cornelis社の新ファブリック「CN500」、AI通信を6倍高速化しInfiniBan…

4. 知識の応用例を検索する新手法「RAG+」、Qwen2.5-72Bモデルで推論精度を最大10…

---

## 1. サイバー犯罪者が、フィッシングメール作成などに悪用されるAIツール「WormGPT」を、より高性能なAIモデルでアップグレードしている

- サイバー犯罪者が、フィッシングメール作成などに悪用されるAIツール「WormGPT」を、より高性能なAIモデルでアップグレードしている。これにより、従来よりも巧妙で説得力のある悪意あるコンテンツの生成が可能となり、サイバー攻撃の脅威が増大している。

- 特に注目すべきは、イーロン・マスク氏のxAI社が開発したAIモデル「Grok」を悪用する新亜種の登場である。犯罪者はカスタムのジェイルブレイク（制限解除）を施し、API経由でGrokの能力を不正に利用して攻撃を高度化させている。

- WormGPTのような犯罪用AIツールの進化は、正規のAIサービスがAPIを通じて不正利用されるリスクを浮き彫りにする。AI開発企業側には、悪用を検知し防止するためのより強固なセキュリティ対策と監視体制の構築が急務となっている。

> **The Decoder** (https://the-decoder.com/cybercriminals-are-upgrading-wormgpt-with-new-ai-models-to-power-more-advanced-attacks/): Cybercriminals are upgrading WormGPT with new AI models to power more advanced attacks
> 【翻訳】犯罪者向けAI「WormGPT」が新モデルで進化。より巧妙で説得力のあるフィッシングメールを生成し、サイバー攻撃の脅威が拡大。

## 2. OpenAI、Instagram、Uberなどで製品開発を率いたPeter Deng氏が、自身の経験を共有

- OpenAI、Instagram、Uberなどで製品開発を率いたPeter Deng氏が、自身の経験を共有。同氏はChatGPTやInstagramフィルター、Facebook News Feedなど数十億人規模の製品構築に貢献し、現在はFelicisで投資家として活動している。

- 同氏はプロダクトマネージャー（PM）を5つの原型に分類するフレームワークを提唱。多様な強みを持つPMを組み合わせることで、課題解決能力の高い「アベンジャーズ」のような強力な製品開発チームを構築できると説明している。

- 製品開発において「製品そのものは（おそらく）重要ではない」という逆説的な視点を提示。技術的な大発見がなくとも、データフライホイールや優れたワークフローを構築することで、巨大なビジネスを築くことが可能であるという教訓を共有した。

- ChatGPTの開発経験から、AIとAGI（汎用人工知能）に関する洞察を披露。特に、AIが個人の学習スタイルに合わせて最適化された教育を提供するなど、教育分野の未来を大きく変革する可能性について議論した。

> **Lennys Podcast Youtube** (https://www.youtube.com/watch?v=8TpakBfsmcQ): From ChatGPT to Instagram to Uber: The quiet architect behind the world’s most popular products
> 【翻訳】ChatGPTやInstagram、Uberの成功を支えたPeter Deng氏。数十億人規模の製品を率いた「静かなる設計者」が、その開発哲学を明かす。

## 3. Cornelis社の新ファブリック「CN500」、AI通信を6倍高速化しInfiniBandを超える性能で市場に登場。

- 米Cornelis Networks社が、AIとHPC向けに最適化された新ネットワークファブリック「CN500」を発表。Ethernet、InfiniBandに次ぐ第3の主要技術として、大規模並列コンピューティングの課題解決を目指す。

- AIアプリケーションにおいて、CN500は既存のEthernetベースのプロトコルと比較して通信速度を6倍に高速化すると主張。これにより、大規模言語モデルのトレーニング時間短縮と効率向上が期待される。

- HPC分野では、最新規格のInfiniBand NDRを凌駕する性能を謳っており、1秒あたりのメッセージ転送数が2倍に増加し、レイテンシは35%低減されることで、計算完了時間をより高速かつ予測可能にする。

- この新技術は、現在の規模を桁違いに上回る最大50万台のコンピュータやプロセッサを、通信遅延を追加することなく接続可能。AIデータセンターの性能を飛躍的に向上させるスケーラビリティを持つ。

> **Ieee Spectrum Ai** (https://spectrum.ieee.org/ai-network-architecture): Could a Data Center Rewiring Lead to 6x Faster AI?
> 【翻訳】米Cornelis NetworksがAIを最大6倍高速化する新ネットワーク「CN500」を発表。InfiniBandに代わる第3の選択肢として、大規模AIの通信ボトルネック解消を目指す。

## 4. 知識の応用例を検索する新手法「RAG+」、Qwen2.5-72Bモデルで推論精度を最大10%向上

- 従来のRAGが知識検索に留まる課題に対し、新手法「RAG+」は知識の応用例（推論過程や実例）も同時に検索するモジュラーフレームワークを提案。これにより、LLMに具体的な手続き的ガイダンスを与え、推論タスクの精度と解釈性を向上させる。

- RAG+は、事実知識とタスク応用例の2つのコーパスを並行して利用する。特定の検索手法やモデルに依存しないプラグアンドプレイ設計のため、既存のRAGシステムにファインチューニングなしで容易に導入できる点が特徴である。

- 数学問題（MathQA）や法的判決予測などの評価で、RAG+は従来のRAGを平均2.5-7.5%上回る性能を達成した。特に大規模モデルQwen2.5-72Bでは最大10%の性能向上が確認され、モデル規模が大きいほど恩恵が大きくなる傾向がある。

> **Ai Newsletter Saravia** (https://nlp.elvissaravia.com/p/top-ai-papers-of-the-week-f9a): 🥇Top AI Papers of the Week
> 【翻訳】次世代技術「RAG+」がLLMの推論を革新。知識だけでなく「解き方」も検索し、精度と解釈性を両立。複雑な問題解決能力が新たなステージへ。

