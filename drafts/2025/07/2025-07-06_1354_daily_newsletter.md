# 2025年07月06日 AI NEWS TLDR

## AI・Claudeの企業活用と技術進展

OpenAIが1000万ドル以上の大口顧客向けにPalantir型のコンサルティングサービスを拡大する動きは、企業がAIを活用した業務改革を本格化させる転換点となっています。

Agentica社とTogether AI社が共同開発した「DeepSWE-Preview」は、強化学習のみで訓練された32Bパラメータのコーディングエージェントとして、プログラマーの作業効率を飛躍的に高める可能性を秘めています。

コンテキストエンジニアリングやClaude Code Hookなどの新技術は、AIと人間の協働をより直感的かつ効果的にし、専門知識がなくても誰もが高度なAI活用スキルを身につけられる未来を切り拓きます。

## 目次

1. LLMの技術でLLMを実現🆙

2. Anthropic、Claude Code Hook新機能で決定論的制御を実現、開発者向け完全ガイド公開🆙

3. AgenticaとTogether AI、強化学習のみで訓練したDeepSWE-Previewが42.2%...🆙

4. OpenAI、コンサルティングで1000万達成🆙

5. LLM（大規模言語モデル）🆙

---

## 1. LLMの技術でLLMを実現🆙

- コンテキストエンジニアリングは、多くの研究者が「死ぬ」と予測していたプロンプトエンジニアリングが進化した形態で、LLMが効果的にタスクを実行するために必要な指示と関連情報を戦略的に設計・調整するプロセスです。

- 従来の「ブラインドプロンプティング」（ChatGPTなどへの単純な質問）とは異なり、コンテキストエンジニアリングでがプロンプトの文脈と構造を慎重に考慮し、知識の取得・強化・最適化のためのより厳密な方法論を採用します。

- 開発者の視点では、コンテキストエンジニアリングが望ましい結果を達成するために指示と提供するコンテキストを最適化する反復的なプロセスであり、評価パイプラインなどの正式なプロセスを通じて戦術の有効性を測定します。

- Dex Horthyの図を基に構築されるこの概念は、Ankur Goyal、Walden Yan、Tobi Lutke、Andrej Karpathyなど多くの専門家によって既に議論されており、AIエージェントワークフローの開発における実践的なステップバイステップガイドとして活用できます。

> **Ai Newsletter Saravia** (https://nlp.elvissaravia.com/p/context-engineering-guide): Context Engineering Guide
> LLMの出力を制御するContext Engineeringの実践ガイド。プロンプト設計、RAG実装、ハルシネーション対策など、具体的な技術手法を網羅。

---

## 2. Anthropic、Claude Code Hook新機能で決定論的制御を実現、開発者向け完全ガイド公開🆙

<div style="margin: 16px 0;">
  <img src="https://gzzrthvxcmwjieqdtoxf.supabase.co/storage/v1/object/public/ainews-images/1751777682_zenndev_20250705_786_d93fa63f.jpg" alt="Anthropic、Claude Code Hook新機能で決定論的制御を実現、開発者向け完全ガイド公開🆙" style="width: 100%; max-width: 600px; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />
</div>

- Claude Code Hookは、Claude Codeのライフサイクルの特定時点で自動実行されるユーザー定義のシェルコマンドであり、LLMの確率的な動作でがなく決定論的な制御を実現する機能です。

- このツールは包括的なリファレンスとして提供されており、基本概念とアーキテクチャ、Hookイベントの種類と機能、作成方法とAPIリファレンスなどの情報が体系的に整理されています。

- 実用例とベストプラクティス、トラブルシューティング、よくある質問なども含まれており、Claude Codeを効果的に活用するための完全ガイドとして機能しています。

> **Zenn Ai General** (https://zenn.dev/usiro/articles/6d282e32c19038): Claude Code Hook 完全ガイド
> Anthropicの新API機能『Claude Code Hook』を活用したコード実行環境の構築方法と実装例。Python、JavaScript対応で、セキュリティ制約やエラーハンドリング

---

## 3. AgenticaとTogether AI、強化学習のみで訓練したDeepSWE-Previewが42.2%...🆙

- Agentica社とTogether AI社が共同開発したDeepSWE-Previewは、Qwen3-32Bをベースに強化学習のみで訓練された32Bパラメータのコーディングエージェントで、SWE-Bench-Verifiedで42.2%のPass@1と71.0%のPass@16を達成しています。

- DeepSWEがAgentica社のrLLMシステムを使用して、R2E-Gymベンチマークの4,500件の実世界ソフトウェアエンジニアリングタスクで訓練され、実際のコードベースのナビゲーション、コード編集、テストスイートでの修正検証が可能になっています。

- 安定した強化学習アルゴリズムGRPO++が導入され、コンパクトフィルタリングや報酬正規化の除去などの革新により、長期的かつ複数ステップのエージェントタスクにおける学習安定性が向上しています。

- 純粋な強化学習訓練から、エッジケースの推論、ステップ複雑性に応じた思考トークンの割り当て、回帰テストスイートに対する自己チェックなど、明示的な指示なしに創発的な振る舞いが生まれています。

> **Ai Newsletter Saravia** (https://nlp.elvissaravia.com/p/ai-agents-weekly-deepswe-cursor-12): 🤖 AI Agents Weekly: DeepSWE, Cursor 1.2, Evaluating Multi-Agent Systems, Prover Agent, Top AI Devs News
> DeepSWEがコード生成精度90%達成、Cursor 1.2がリアルタイム協調編集機能実装、マルチエージェント評価フレームワークの登場、数学証明に特化したProver Agentの開発など、

---

## 4. OpenAI、コンサルティングで1000万達成🆙

- OpenAIが1000万ドル以上を支出する「戦略的」アカウント向けにコンサルティングサービスを拡大しており、これがPalantirのようなソフトウェアプラットフォームを中心としたサービス提供モデルに類似しています。

- 2024年後半からForward Deployed Engineers（FDEs）の採用を開始し、大企業アカウントと直接統合する意図を示していたOpenAIは、2025年6月までに年間収益を120億ドルに3倍増させることに成功しています。

- OpenAIのコンサルティング戦略は単なる収益源ではなく、カスタムモデル採用と微調整インフラという2つのトレンドを活用して、企業のテクノロジースタックにOpenAIモデルを深く組み込むための戦略的な足がかりとして機能しています。

- 多くのAIコンサルティング企業が浅すぎる製品化されたサービスと利益率を下げるカスタムサービスの間で差別化に苦戦する中、OpenAIが高利益率のビジネスモデルを確立し、その戦略を業界に示しています。

> **Nextword Ai** (https://nextword.substack.com/p/how-to-sell-ai-consulting-at-high): How to Sell AI Consulting at High Margins
> AI導入コンサルティングで300%の利益率を実現する5つの戦略：価値ベース価格設定と業界特化ソリューションが鍵

---

## 5. LLM（大規模言語モデル）🆙

<div style="margin: 16px 0;">
  <img src="https://gzzrthvxcmwjieqdtoxf.supabase.co/storage/v1/object/public/ainews-images/1751777682_zenndev_20250705_8e5_8682b6ea.jpg" alt="LLM（大規模言語モデル）🆙" style="width: 100%; max-width: 600px; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />
</div>

- LLM（大規模言語モデル）学習のための体系的なロードマップが5つのフェーズで構成されており、初学者から専門家まで段階的に知識を積み上げられる構造になっています。

- 基礎知識の習得から始まり、モデルの理解、プロンプトエンジニアリング、実装技術、そして応用分野へと進む体系的なアプローチにより、LLM技術の全体像を効率的に把握できます。

- 各フェーズには具体的な学習リソースや参考文献が提示されており、自己学習のガイドラインとして活用できるだけでなく、実務での応用を見据えた実践的な内容となっています。

- このロードマップは技術の進化に合わせて更新される可能性があり、LLM分野の急速な発展に対応するための継続的な学習フレームワークとして機能します。

> **Zenn Llm** (https://zenn.dev/foxgem/articles/5f5bc2fe3abc7c): LLM学習ロードマップ
> 初心者から上級者まで体系化されたLLM習得ステップ。基礎理論→Hugging Face実装→RAG構築→微調整技術→評価指標まで、実務スキル獲得の最短経路を網羅

---

## Lawrence's Insights

*※ここにLawrenceさんの手入力コメントを追加してください*

---
