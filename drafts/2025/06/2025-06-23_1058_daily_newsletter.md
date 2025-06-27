# 2025年06月23日 AI NEWS TLDR

## Cornelis社CN500とRAG+、…

Cornelis社がAI通信を6倍高速化する新ファブリック「CN500」を発表し、インフラ競争が激化。

一方、新フレームワーク「RAG+」はLLMの推論精度を10%向上させるなど、応用技術も進化を続けています。

しかしxAI社の「Grok」を悪用した「WormGPT」も登場し、サイバー攻撃の巧妙化という負の側面も顕在化しています。

それでは各トピックの詳細を見ていきましょう。

## 目次

1. 米Cornelis Networks社が

2. 従来のRAGの課題を解決する新フレームワーク「RAG+」が提案された

3. サイバー犯罪者が、フィッシングメール作成などに悪用されるAIツール「WormGPT」を、よ…

---

## 1. 米Cornelis Networks社が

- 米Cornelis Networks社が、AIやHPC向けに最適化された新ネットワークファブリック「CN500」を発表。EthernetやInfiniBandに次ぐ第3の主要ネットワーク技術として、大規模並列コンピューティングの課題解決を目指す。

- AIアプリケーションにおいて、CN500は従来のEthernetベースのプロトコルと比較して通信速度を6倍に高速化する。これにより、大規模言語モデルのトレーニングなどで求められる数万台規模のサーバー間通信を効率化する。

- HPC分野では、最新規格のInfiniBand NDRと比較して1秒あたりのメッセージ転送数が2倍、遅延は35%少ない性能を主張。最大50万台のコンピュータを遅延なく接続可能で、従来を大幅に上回るスケーラビリティを実現する。

- 既存のネットワーク技術は小規模なローカル接続を前提としていたが、CN500はAI時代の大規模データセンターにおけるサーバー間の高速・高効率な連携という現代的な要求に応えるために設計されている。

> **Ieee Spectrum Ai** (https://spectrum.ieee.org/ai-network-architecture): Could a Data Center Rewiring Lead to 6x Faster AI?
> 【翻訳】米Cornelis NetworksがAIを最大6倍高速化する新ネットワーク「CN500」を発表。Ethernet等に代わる第3の選択肢として、大規模AIの通信ボトルネック解消を目指す。

## 2. 従来のRAGの課題を解決する新フレームワーク「RAG+」が提案された

- 従来のRAGの課題を解決する新フレームワーク「RAG+」が提案された。事実知識に加え、タスク固有の応用例（推論過程など）を同時に検索するデュアルコーパス方式を採用し、LLMに明確な手続き的ガイダンスを与え、推論精度を向上させる。

- MathQAやMedQA、法的判決予測などの評価において、RAG+は従来のRAGを平均2.5～7.5%上回る性能を達成。特にQwen2.5-72Bのような大規模モデルを用いた法的推論では、最大10%という顕著な改善を示した。

- このシステムは特定のモデルに依存しないプラグアンドプレイ設計で、既存のRAGに容易に導入可能。さらに、Qwen2.5-72Bのような強力なLLMによるリランキングと組み合わせることで、小規模モデルの性能を最大7%向上させる相乗効果も確認された。

> **Ai Newsletter Saravia** (https://nlp.elvissaravia.com/p/top-ai-papers-of-the-week-f9a): 🥇Top AI Papers of the Week
> 【翻訳】RAGの精度を飛躍させる新手法「RAG+」が登場。事実と推論例を同時に検索するデュアルコーパス方式で、LLMにタスクの「手順書」を提示し、複雑な問題解決能力を強化する。

## 3. サイバー犯罪者が、フィッシングメール作成などに悪用されるAIツール「WormGPT」を、より高性能なAI...

- サイバー犯罪者が、フィッシングメール作成などに悪用されるAIツール「WormGPT」を、より高性能なAIモデルで強化していることが判明した。これにより、従来よりも巧妙で検知しにくいサイバー攻撃が実行される危険性が高まっている。

- 新たな亜種の一つとして、イーロン・マスク氏率いるxAI社が開発したAIモデル「Grok」を不正利用するものが確認された。APIを介してGrokの能力にアクセスし、より高度な攻撃コンテンツを生成する仕組みとなっている。

- Grokを悪用するWormGPTは、AIの安全機能を無効化するカスタムの「ジェイルブレイク」プロンプトを使用している。これにより、本来は制限されているはずの悪意のあるタスクを実行させ、攻撃の巧妙化を実現している。

> **The Decoder** (https://the-decoder.com/cybercriminals-are-upgrading-wormgpt-with-new-ai-models-to-power-more-advanced-attacks/): Cybercriminals are upgrading WormGPT with new AI models to power more advanced attacks

