# 2025年06月23日 AI NEWS TLDR

## NVIDIAの「Huangの法則」とCornelisの高速化技術、AI性能競争の新局面

NVIDIAのTensor Coreは「Huangの法則」で性能を飛躍させ、AI開発の基盤を支えています。

一方、Cornelis Networksは新ファブリック「CN500」でデータセンターを最大6倍高速化する新アーキテクチャを発表。

ソフトウェア分野でも応用推論を組み込んだ「RAG+」が登場し、AIの進化はハードとソフトの両面で加速しています。

それでは各トピックの詳細を見ていきましょう。

## 目次

1. Cornelis Networksが開発したCN500ネットワークファブリックは

2. ムーアの法則を超え「Huangの法則」を体現。NVIDIA Blackwellが示すTensor C…

3. 新フレームワーク「RAG+」、既存システムに推論能力を後付けし性能を最大10%向上

4. 研究者たちはマルチモーダルAIモデルに数学的推論能力を習得させる新たな方法として、数学データセット

5. Peter Dengは、OpenAI、Instagram、Uber

6. サイバー犯罪者たちがマルウェア作成ツール「WormGPT」を強力なAIモデルで強化しており

---

## 1. Cornelis Networksが開発したCN500ネットワークファブリックは

- Cornelis Networksが開発したCN500ネットワークファブリックは、最大50万台のコンピュータやプロセッサを接続可能で、レイテンシを増加させずにAIパフォーマンスを最大化する新アーキテクチャです。

- この技術はEthernetとInfiniBandに続く第三のネットワーキング製品として登場し、AIと高性能コンピューティング(HPC)向けに設計され、より高速で予測可能な処理時間と効率性を実現します。

- Cornelisによれば、HPC用途では2022年導入のInfiniBand NDRと比較して1秒あたり2倍のメッセージ処理と35%低いレイテンシを実現し、AI用途ではEthernetベースのプロトコルと比較して6倍高速な通信を提供します。

- 従来のEthernetやInfiniBandは少数のローカルデバイス接続用に設計されていたのに対し、CN500は並列コンピューティングとAI時代の大規模データセンター向けに最適化されています。

> **Ieee Spectrum Ai** (https://spectrum.ieee.org/ai-network-architecture): Could a Data Center Rewiring Lead to 6x Faster AI?
> 【翻訳】Cornelis NetworksのCN500、AI性能を最大6倍高速化。50万台規模のプロセッサを低遅延で接続する新アーキテクチャで、データセンターのボトルネックを解消。

## 2. ムーアの法則を超え「Huangの法則」を体現。NVIDIA Blackwellが示すTensor Coreの進化

- NVIDIAのTensor Coreは現代のAIと機械学習の基盤技術であり、ムーアの法則を超えるペースで「Huangの法則」と呼ばれる性能向上を実現している重要コンポーネントです。

- 2022年末の「AI Scaling Laws」記事で議論されたように、AIの能力向上はトレーニングと推論の最適化だけでなく、GPU計算能力の急速な進化によって支えられています。

- 従来のDennardスケーリングやムーアの法則が限界を迎える中、先進パッケージング技術、3Dスタッキング、新型トランジスタ、GPUなどの専用アーキテクチャが計算能力向上の主役となっています。

- 記事ではVoltaからBlackwellに至るNVIDIAのデータセンターGPUの主要機能と性能エンジニアリングの基本原則を解説し、Tensor Coreの進化を追跡しています。

> **Semianalysis** (https://semianalysis.com/2025/06/23/nvidia-tensor-core-evolution-from-volta-to-blackwell/): NVIDIA Tensor Core Evolution: From Volta To Blackwell
> 【翻訳】NVIDIAのTensor CoreはVoltaからBlackwellへ驚異の進化。7年間でAI性能を1000倍に高め、「Huangの法則」でAI革命を牽引する。

## 3. 新フレームワーク「RAG+」、既存システムに推論能力を後付けし性能を最大10%向上

- 「RAG+」という新しいフレームワークが発表され、従来のRAGシステムに応用レベルの推論を明示的に組み込むことで性能を向上させています。このモジュラー設計は知識だけでなく、タスク固有の応用例（ステップバイステップの推論過程など）も取得する二重コーパス検索を特徴としています。

- RAG+はプラグアンドプレイ設計を採用しており、微調整や構造変更が不要なため、既存のRAGシステムに容易に応用認識機能を追加できます。検索に依存せず、モデルにも依存しない汎用性の高いアプローチです。

- 数学（MathQA）、医療（MedQA）、法的判断予測などの分野での評価では、RAG+は従来のRAGバリアントと比較して平均2.5〜7.5%のパフォーマンス向上を示し、Qwen2.5-72Bのような大規模モデルでは法的推論において最大10%の向上が見られました。

- より大きなモデルほどRAG+の恩恵を受けやすく、特に強力なLLMによるリランキングと組み合わせると効果的です。例えば、Qwen2.5-72Bによるリランキングは小規模モデルのパフォーマンスを最大7%向上させました。

> **Ai Newsletter Saravia** (https://nlp.elvissaravia.com/p/top-ai-papers-of-the-week-f9a): 🥇Top AI Papers of the Week
> 【翻訳】RAGは推論の時代へ。新フレームワーク「RAG+」は知識と推論過程を二重検索し、応用レベルの思考力で性能を向上。

## 4. 研究者たちはマルチモーダルAIモデルに数学的推論能力を習得させる新たな方法として、数学データセット

- 研究者たちはマルチモーダルAIモデルに数学的推論能力を習得させる新たな方法として、数学データセットではなくSnakeやTetrisのような単純なアーケードゲームのプレイが効果的であることを発見しました。

- この発見は従来の数学学習アプローチとは異なり、ゲームプレイを通じた実践的な問題解決が数学的思考能力の開発に役立つ可能性を示唆しています。

- この研究はAIの学習方法に関する新たな視点を提供し、実世界の問題解決とゲーム環境での学習の関連性を強調しています。

- THE DECODERが最初に報じたこの研究は、AIトレーニング手法の多様化と、数学的推論能力獲得の新たなパラダイムを示しています。

> **The Decoder** (https://the-decoder.com/ai-learns-math-reasoning-by-playing-snake-and-tetris-like-games-rather-than-using-math-datasets/): AI learns math reasoning by playing Snake and Tetris-like games rather than using math datasets
> 【翻訳】Google DeepMind、AIにテトリス等をプレイさせ数学能力を向上。数学データなしでベンチマークスコアが15%向上し、ゲームから抽象的推論を学ぶ新手法を実証。

## 5. Peter Dengは、OpenAI、Instagram、Uber

- Peter Dengは、OpenAI、Instagram、Uber、Facebookなど複数の大手テック企業でプロダクトチームを率い、ChatGPT、Instagramフィルター、Facebook News Feedなど数十億人が使用する製品開発に貢献した人物で、現在はFelicisで初期段階のスタートアップ創業者への投資を行っています。

- 彼はプロダクトマネージャーを5つのアーキタイプに分類し、それぞれの強みを活かした「アベンジャーズ」のようなチーム構築を提唱しており、優秀な人材採用には独自の「一文テスト」を用いています。

- Dengは製品そのものよりもユーザーの問題解決に焦点を当てるべきだと主張し、必ずしも技術的ブレークスルーがなくても大規模ビジネスを構築できると説いています。

- プロダクト成長において、0から1、1から100へのスケーリングに関する直感に反する教訓や、データフライホイールとワークフローの重要性についても言及しています。

> **Lennys Podcast Youtube** (https://www.youtube.com/watch?v=8TpakBfsmcQ): From ChatGPT to Instagram to Uber: The quiet architect behind the world’s most popular products
> 【翻訳】ChatGPT、インスタ、Uberを渡り歩いた「静かな建築家」Peter Deng氏。数十億人が使う製品を生んだ彼が、今度は投資家として次世代のヒットを狙う。

## 6. サイバー犯罪者たちがマルウェア作成ツール「WormGPT」を強力なAIモデルで強化しており

- サイバー犯罪者たちがマルウェア作成ツール「WormGPT」を強力なAIモデルで強化しており、より高度なサイバー攻撃の実行が可能になっています。

- 新たなWormGPTの亜種の一つはxAI社の大規模言語モデル「Grok」のAPIにカスタムジェイルブレイク手法を用いてアクセスし、悪意ある目的に活用しています。

- この進化したWormGPTは、フィッシング詐欺やマルウェア開発などの犯罪活動をAI支援により効率化・高度化させる危険性があります。

- THE DECODERが最初に報じたこの事例は、AIモデルの悪用防止対策の重要性と、サイバーセキュリティ上の新たな脅威の出現を示しています。

> **The Decoder** (https://the-decoder.com/cybercriminals-are-upgrading-wormgpt-with-new-ai-models-to-power-more-advanced-attacks/): Cybercriminals are upgrading WormGPT with new AI models to power more advanced attacks
> 【翻訳】サイバー犯罪ツール「WormGPT」、新AIモデル搭載で攻撃能力が進化。巧妙なマルウェアやフィッシング文を自動生成し、企業のセキュリティリスクがかつてなく高まっています。

