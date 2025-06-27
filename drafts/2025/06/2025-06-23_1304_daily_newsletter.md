# 2025年06月23日 AI NEWS TLDR

## Cornelisの6倍高速化とRAG+の性能向上、Grok悪用によるサイバーリス…

Cornelis Networks社は新製品「CN500」でAI通信を6倍高速化し、大規模モデル開発の加速を目指す。

また、新手法「RAG+」は応用例の検索により、LLMの推論性能を10%向上させる画期的な成果を示した。

その裏でxAI社のGrokが悪用された「WormGPT」も登場し、AIの進化に伴うセキュリティリスクが顕在化している。

それでは各トピックの詳細を見ていきましょう。

## 目次

1. 米Cornelis Networks社が

2. 応用例も検索する新手法「RAG+」、Qwen2-72Bで法的推論の精度10%向上

3. 悪意あるAI「WormGPT」、xAI社の「Grok」を悪用し進化。巧妙化するサイバー攻撃の新たな脅威。

---

## 1. 米Cornelis Networks社が

- 米Cornelis Networks社が、AI向けに最適化された新ネットワークファブリック「CN500」を発表。従来のEthernetベースのプロトコルと比較して6倍高速な通信を実現し、大規模言語モデルのトレーニングにおけるサーバー間の遅延を解消する。

- HPC（スーパーコンピュータ）分野においても、最新のInfiniBand NDRを凌駕する性能を主張。1秒あたりのメッセージ転送数を2倍に増やし、レイテンシを35%低減することで、計算完了時間の短縮と予測可能性の向上に貢献する。

- CN500は最大50万台のコンピュータやプロセッサを遅延なく接続できる高いスケーラビリティを持つ。小規模接続を前提としたEthernetやInfiniBandとは異なり、大規模並列コンピューティングの課題解決を目的として設計されている。

> **Ieee Spectrum Ai** (https://spectrum.ieee.org/ai-network-architecture): Could a Data Center Rewiring Lead to 6x Faster AI?
> 【翻訳】米Cornelis NetworksがAI向け新通信技術「CN500」を発表。従来比6倍の速度でサーバー間遅延を解消し、LLMのトレーニングを劇的に高速化へ。

## 2. 応用例も検索する新手法「RAG+」、Qwen2-72Bで法的推論の精度10%向上

- 従来のRAGを拡張する新フレームワーク「RAG+」が提案された。これは、関連知識だけでなく、その知識をどう活用するかの「応用例」も同時に検索するデュアルコーパス方式を採用し、LLMにタスク解決のための具体的な手順や推論プロセスを提供する。

- 数学問題（MathQA）や医療QA（MedQA）、法的推論などの専門分野で評価され、従来のRAG手法を平均2.5～7.5%上回る性能を達成。特にQwen2.5-72Bのような大規模モデルでは、法的推論タスクで最大10%という顕著な性能向上が報告されている。

- RAG+は特定のモデルや検索手法に依存しないプラグアンドプレイ設計が特徴で、既存のRAGシステムにファインチューニング不要で導入可能。大規模モデルほど恩恵が大きく、強力なLLMによるリランキングと組み合わせることで、小規模モデルの性能も最大7%向上させるなど高い拡張性を持つ。

> **Ai Newsletter Saravia** (https://nlp.elvissaravia.com/p/top-ai-papers-of-the-week-f9a): 🥇Top AI Papers of the Week
> 【翻訳】次世代RAG「RAG+」はLLMの推論力を向上。知識と「応用例」をデュアル検索し、より複雑なタスク解決を可能にする。

## 3. 悪意あるAI「WormGPT」、xAI社の「Grok」を悪用し進化。巧妙化するサイバー攻撃の新たな脅威。

- サイバー犯罪者が、フィッシング詐欺などの攻撃を自動化する悪意あるAIツール「WormGPT」を、より強力なAIモデルでアップグレードしていることが報告された。これにより、さらに高度で検知が困難な攻撃が可能になる懸念が高まっている。

- 新たな亜種の一つとして、イーロン・マスク氏率いるxAI社のAIモデル「Grok」を悪用するものが確認された。APIとカスタムのジェイルブレイク（制限解除）手法を組み合わせ、Grokの安全機能を回避して攻撃的なコンテンツを生成させている。

- この動向は、公開されているAIモデルのAPIが、容易に犯罪ツールに統合されうるという深刻なリスクを浮き彫りにしている。Grokのような最新モデルの悪用は、サイバー攻撃の巧妙化と大規模化を加速させる可能性がある。

> **The Decoder** (https://the-decoder.com/cybercriminals-are-upgrading-wormgpt-with-new-ai-models-to-power-more-advanced-attacks/): Cybercriminals are upgrading WormGPT with new AI models to power more advanced attacks
> 【翻訳】サイバー犯罪者が悪意あるAI「WormGPT」を新モデルで強化。検知困難で、より巧妙なフィッシング攻撃の自動化に懸念。

