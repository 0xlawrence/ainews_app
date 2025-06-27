# 2025年06月23日 AI NEWS TLDR

## xAI悪用と新RAG、AI進化の光と影

新RAGフレームワーク「RAG+」が法律分野の推論精度を最大10%向上させるなど、専門領域での技術応用が進展しています。

一方で犯罪AI「WormGPT」はxAI社のGrokを悪用して進化し、フィッシング攻撃の巧妙化という脅威も増大。

こうした中、ChatGPTの立役者は「製品自体は重要ではない」という逆説的な事業成長の鍵を語ります。

それでは各トピックの詳細を見ていきましょう。

## 目次

1. サイバー犯罪者が、フィッシング詐欺などを自動化するAIツール「WormGPT」を、より高性…

2. OpenAIのChatGPTやMetaのInstagramフィルターなど、数十億人規模の製…

3. 従来のRAGの課題を解決する新フレームワーク「RAG+」が提案された

4. 米Cornelis Networks社が

---

## 1. サイバー犯罪者が、フィッシング詐欺などを自動化するAIツール「WormGPT」を、より高性能なAIモデル...

- サイバー犯罪者が、フィッシング詐欺などを自動化するAIツール「WormGPT」を、より高性能なAIモデルで強化していることが判明。これにより、攻撃の巧妙化と大規模化が懸念されている。

- 新たな亜種の一つでは、イーロン・マスク氏率いるxAI社が開発したAIモデル「Grok」がAPI経由で悪用されている。これは、Grokの高度な言語能力をサイバー攻撃に転用する動きを示している。

- GrokのAPIを利用する際、サイバー犯罪者は安全上の制限を回避するためのカスタム「ジェイルブレイク」プロンプトを使用しており、本来は禁止されている悪意のあるコンテンツ生成を可能にしている。

> **The Decoder** (https://the-decoder.com/cybercriminals-are-upgrading-wormgpt-with-new-ai-models-to-power-more-advanced-attacks/): Cybercriminals are upgrading WormGPT with new AI models to power more advanced attacks

## 2. OpenAIのChatGPTやMetaのInstagramフィルターなど、数十億人規模の製品開発を率いた...

- OpenAIのChatGPTやMetaのInstagramフィルターなど、数十億人規模の製品開発を率いたPeter Deng氏が、自身の経験に基づく知見を共有。同氏は現在、VCのFelicisで初期段階の創業者に投資している。

- プロダクトマネージャーをビジョナリーやアーキテクトなど5つの原型に分類し、多様な強みを持つ「アベンジャーズ」のようなチームを構築する重要性を強調。これが複雑な課題解決と製品の成功に繋がるとした。

- 「製品自体は重要ではない」という逆説的な視点を提示。技術的ブレークスルーよりも、ユーザーのワークフローを深く理解し、データフライホイールを構築することが事業成長の鍵であると解説した。

- ChatGPTの開発経験に基づき、AIが教育分野に与える影響について言及。AIによる個別指導の民主化が、学習体験を根本的に変革する大きな可能性を秘めているとの見解を示した。

> **Lennys Podcast Youtube** (https://www.youtube.com/watch?v=8TpakBfsmcQ): From ChatGPT to Instagram to Uber: The quiet architect behind the world’s most popular products
> 【翻訳】ChatGPTやInstagram、Uberなど数十億人規模の製品を率いたPeter Deng氏が、その成功の秘訣を公開。現在はVCとして次世代の創業者を支援。

## 3. 従来のRAGの課題を解決する新フレームワーク「RAG+」が提案された

- 従来のRAGの課題を解決する新フレームワーク「RAG+」が提案された。事実知識だけでなく、その知識の具体的な「応用例」も同時に検索するデュアルコーパス検索を採用し、LLMに明示的な手続き的ガイダンスを提供することで、推論タスクの精度と解釈可能性を向上させる。

- 数学問題（MathQA）や医療（MedQA）、法律分野の評価において、RAG+は従来のRAG手法を平均2.5〜7.5%上回る性能を達成した。特にQwen2.5-72Bのような大規模モデルと組み合わせた場合、法律分野の推論タスクで最大10%の性能向上を示し、その有効性が実証されている。

- RAG+は特定の検索手法やモデルに依存しないプラグアンドプレイ設計が特徴で、ファインチューニングなしで既存のRAGシステムに容易に統合できる。モデル規模が大きいほど性能向上の恩恵を受けやすく、強力なLLMによるリランキングを併用することで、さらに最大7%の性能ブーストが確認された。

> **Ai Newsletter Saravia** (https://nlp.elvissaravia.com/p/top-ai-papers-of-the-week-f9a): 🥇Top AI Papers of the Week
> 【翻訳】はい、承知いたしました。
以下に、ご要望に沿った形で要約翻訳を作成します。

**翻訳:**

## 4. 米Cornelis Networks社が

- 米Cornelis Networks社が、AIやHPC向けに最適化された新ネットワークファブリック「CN500」を発表。EthernetやInfiniBandに次ぐ第3の主要技術として、大規模並列コンピューティングの課題解決を目指す。

- AIアプリケーションにおいて、CN500はEthernetベースのプロトコルと比較して通信速度を6倍に高速化。数万台規模のサーバーを協調させる大規模言語モデルの学習などで、より迅速かつ予測可能な処理完了を実現する。

- HPC分野では、最新のInfiniBand NDRと比較して1秒あたりのメッセージ転送数が2倍、遅延を35%削減。最大50万台のコンピュータを遅延なく接続可能とし、桁違いの規模を持つスーパーコンピュータ構築を支援する。

> **Ieee Spectrum Ai** (https://spectrum.ieee.org/ai-network-architecture): Could a Data Center Rewiring Lead to 6x Faster AI?
> 【翻訳】米Cornelis Networksの新ファブリック「CN500」はAIを最大6倍高速化する可能性。Ethernet/InfiniBandに次ぐ第3の勢力として大規模計算に革新をもたらすか。

