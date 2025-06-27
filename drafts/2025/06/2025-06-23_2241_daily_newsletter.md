# 2025年06月23日 AI NEWS TLDR

## NVIDIAの「Huangの法則」と新技術「RAG+」、OpenAIの商標紛争

NVIDIAのTensor Coreが「Huangの法則」と呼ばれるペースで進化を遂げ、AIのハードウェア基盤を強化しています。

ソフトウェア層では、推論能力を向上させる新フレームワーク「RAG+」が発表され、技術革新がさらに加速。

一方、OpenAIは商標紛争で「io」プロジェクトを全削除するなど、急成長に伴う法務リスクも顕在化しました。

それでは各トピックの詳細を見ていきましょう。

## 目次

1. OpenAI、IYO Audio社との商標衝突で新プロジェクト「io」の情報を公式サイトから全削除

2. NVIDIA Tensor Coreが示す「Huangの法則」。最新Blackwellで加速するAI計算能力の進化。

3. 「RAG+」という新しいモジュラー登場

4. 犯罪AI「WormGPT」、xAIの「Grok」を不正利用し機能強化。高度なマルウェアを生成

---

## 1. OpenAI、IYO Audio社との商標衝突で新プロジェクト「io」の情報を公式サイトから全削除

- OpenAIは商標紛争を受けて「io」プロジェクトに関する全ての言及をウェブサイトから削除しました。この紛争は同じ発音の「IYO Audio」社との間で発生したものです。

- 「io」はOpenAIが開発中だった新プロジェクトと見られていましたが、IYO Audio社との商標権問題により公式サイトから全ての関連情報が取り下げられる事態となりました。

- この商標紛争はAI業界で増加している知的財産権問題の一例であり、大手AI企業が新プロジェクト名を選定する際の法的リスクを示しています。

> **The Decoder** (https://the-decoder.com/openai-removed-all-mentions-of-its-io-project-after-a-trademark-clash-with-iyo-audio/): OpenAI removed all mentions of its "io" project after a trademark clash with IYO Audio
> 【翻訳】OpenAIの新プロジェクト「io」が商標トラブルで公開停止。IYO Audio社との名称競合で全情報が削除される。

## 2. NVIDIA Tensor Coreが示す「Huangの法則」。最新Blackwellで加速するAI計算能力の進化。

- NVIDIAのTensor Coreは現代のAIと機械学習の基盤技術であり、ムーアの法則を超えるペースで「Huangの法則」と呼ばれる性能向上を実現しています。この技術は業界内でも十分に理解されていない専門性の高い領域です。

- 2022年末のAIスケーリング法則に関する記事では、AIモデルの能力向上とトークンコスト削減が急速に進んでいる背景として、トレーニングと推論の最適化だけでなく、計算能力の向上が重要な役割を果たしていることが指摘されています。

- 従来のDennardスケーリングが2000年代後半に終焉し、トランジスタあたりのコスト削減も2010年代後半に減速したにもかかわらず、先進パッケージング技術や3Dスタッキング、新型トランジスタ、GPUなどの専用アーキテクチャにより計算能力は急速に向上し続けています。

- この記事では、主要データセンターGPUの中核機能を紹介し、パフォーマンスエンジニアリングの基本原則を説明した上で、VoltaからBlackwellに至るTensor Coreの進化を追跡する内容となっています。

> **Semianalysis** (https://semianalysis.com/2025/06/23/nvidia-tensor-core-evolution-from-volta-to-blackwell/): NVIDIA Tensor Core Evolution: From Volta To Blackwell
> 【翻訳】NVIDIAによる最新AI技術動向の詳細分析

## 3. 「RAG+」という新しいモジュラー登場

- 「RAG+」という新しいモジュラーフレームワークが発表され、従来のRAGシステムに「アプリケーションレベルの推論」を明示的に組み込むことで性能を向上させています。このシステムは知識だけでなく、その知識の応用例も同時に取得する二重コーパス検索を特徴としています。

- RAG+は既存のRAGシステムに簡単に組み込める「プラグアンドプレイ」設計で、モデルやリトリーバーの種類を問わず、ファインチューニングや構造変更なしで利用可能です。これにより、あらゆるRAGシステムにアプリケーション認識機能を追加できます。

- MathQA、MedQA、法的判決予測などの分野での評価では、RAG+は従来のRAG手法と比較して平均2.5〜7.5%の性能向上を示し、特にQwen2.5-72Bのような大規模モデルでは法的推論において最大10%の改善が見られました。

- 大規模モデルほどRAG+の恩恵を受けやすく、特に強力なLLMによるリランキングと組み合わせると効果が高まります。例えば、Qwen2.5-72Bによるリランキングは小規模モデルの性能を最大7%向上させました。

> **Ai Newsletter Saravia** (https://nlp.elvissaravia.com/p/top-ai-papers-of-the-week-f9a): 🥇Top AI Papers of the Week
> 【翻訳】次世代RAG「RAG+」が従来の限界を打破。知識と応用例を同時に検索する「二重コーパス検索」で、アプリケーションレベルの推論を実現し、回答精度を大幅に向上させます。

## 4. 犯罪AI「WormGPT」、xAIの「Grok」を不正利用し機能強化。高度なマルウェアを生成

- サイバー犯罪者がマルウェア作成ツール「WormGPT」を強力なAIモデルで強化しており、より高度なサイバー攻撃の実行が可能になっています。

- 新たなWormGPTの亜種の一つはイーロン・マスク率いるxAI社の「Grok」AIモデルをAPIを通じてカスタムジェイルブレイク手法で不正利用していることが判明しました。

- このアップグレードにより、WormGPTはより洗練されたフィッシングメール作成やマルウェアコード生成などの悪意ある活動を効率的に実行できるようになっています。

- 正規のAI技術が犯罪目的に転用される事例が増加しており、AIセキュリティ対策の重要性が高まっています。

> **The Decoder** (https://the-decoder.com/cybercriminals-are-upgrading-wormgpt-with-new-ai-models-to-power-more-advanced-attacks/): Cybercriminals are upgrading WormGPT with new AI models to power more advanced attacks
> 【翻訳】闇のChatGPTと呼ばれる「WormGPT」が最新AIモデルで進化。人間と見分けがつかないフィッシングメールを無制限に生成可能となり、サイバー攻撃の自動化・高度化が深刻な脅威に。

