# 2025年07月03日 AI NEWS TLDR

## LLM・Geminiの企業活用と技術進展

Anthropic社のCEOダリオ・アモデイ氏は、AIの急速な発展により5年以内に新卒レベルの仕事の半分が消滅し、米国の失業率が20%に達する可能性があると警告しています。

一方で、Kwai社が発表した80億パラメータのマルチモーダルモデル「Keye-VL」は短編動画理解に特化しており、現代のデジタルコンテンツ消費傾向に合わせた技術革新を進めています。

OpenAIのChatGPTからGoogleのGeminiまで、企業向けAIツールの実用化が進む中、プログラミング言語Lispの括弧処理など技術的課題も明らかになり、AIの能力限界と実用性のバランスが今後の開発方向性を左右します。

## 目次

1. Gemini ProでWindows PCソフトウェア管理を効率化、Microsoft

2. ChatGPTの誕生秘話、OpenAIが明かす別名候補と開発舞台裏

3. LLMによるAI分野の新展開

4. # 「Kwai社のKeye-VL、80億パラメータで短編動画理解に特化、新ベンチマークも公開

5. AnthropicがAI技術の新展開を発表

6. New RelicがAIエージェントのROI測定手法を公開、可観測性技術で成果を数値化

7. OpenAI、Robinhoodの『OpenAIトークン』販売に警告 株式誤認の懸念表明

---

## 1. Gemini ProでWindows PCソフトウェア管理を効率化、Microsoft

- 記事の著者は、会社でGemini Proが使えるようになったことをきっかけに、AIの業務活用方法を模索していました。それまではChatGPTを文章校正に使う程度でしたが、より実用的な使い道を探していました。

- 著者はMicrosoft Intuneを使ったクライアントPC管理業務に携わっており、顧客企業内で必須のソフトウェアを各PCに配布する作業を担当していました。

- 記事では、Gemini AIを活用して、Windows PCにインストールされているソフトウェアの一覧を取得・分析する方法について解説していると推測されます。

> **The Decoder** (https://the-decoder.com/sciarena-lets-scientists-compare-llms-on-real-research-questions/): SciArenaプラットフォーム。実際の研究課題でLLMの性能を科学者が直接比較可能に。GPT-4やClaude。
> **TechCrunch** (https://techcrunch.com/2025/07/02/ai-job-predictions-become-corporate-americas-newest-competitive-sport/): 米大手企業がAI人材需要を過剰予測する競争激化、McKinseyは2030年までに1億2000万人の雇用転換を予測、実態との乖離が顕著

## 2. ChatGPTの誕生秘話、OpenAIが明かす別名候補と開発舞台裏

- OpenAIのポッドキャスト第2回エピソードで、ChatGPTの責任者ニック・ターリー氏が、ChatGPTの立ち上げ前の日々について語っています。

- ターリー氏の発言によると、現在世界的に知られているChatGPTは、当初は別の名前が検討されていたことが明らかになりました。

- このエピソードの完全版はYouTubeで視聴可能で、ChatGPTの開発背景や命名プロセスについての詳細が語られています。

> **VentureBeat AI** (https://venturebeat.com/ai/transform-2025-why-observability-is-critical-for-ai-agent-ecosystems/): 2025年のAIエコシステムでは。複雑なエージェント間連携を可視化する観測技術が不可欠。障害検出時間を75%短縮し。
> **TechCrunch** (https://techcrunch.com/2025/07/02/openai-condemns-robinhoods-openai-tokens/): OpenAIが証券会社Robinhoodの『OpenAI tokens』商標に対し法的措置を警告。AIブランド名の無断使用と投資家誤認を招く暗号資産販売に強く反発

## 3. LLMによるAI分野の新展開

- 記事では、大規模言語モデル（LLM）がLisp言語の括弧処理を苦手とする理由について探求しています。Pythonなど他のプログラミング言語と比較して、Lispでは括弧の正確な対応が特に重要です。

- 著者は、LLMのLisp処理の困難さを、Transformerベースモデルが直面する「ストロベリー問題」（特定の要素を正確に数える能力の限界）と関連付けて考察しています。

- この記事は「o3ちゃんはLispの括弧を閉じれない」という以前の投稿の続編として位置づけられており、コーディングエージェントの言語処理能力の限界についてより深く掘り下げています。

> **Zenn Llm** (https://zenn.dev/kiyoka/articles/coding-agent-2): LLMはS式の再帰的構造解析が苦手で、Lispの括弧の深いネストやマクロ展開を正確に追跡できない。GPT-4でもLispコードの括弧バランス維持に失敗する傾向が顕著

## 4. # 「Kwai社のKeye-VL、80億パラメータで短編動画理解に特化、新ベンチマークも公開

- Kwai Keye-VLは、短編動画理解に特化した80億パラメータのマルチモーダル基盤モデルで、一般的な視覚言語能力も維持しながら、現代のデジタル環境で主流となっている動的な短編動画の理解を強化しています。

- このモデルは、6000億トークン以上の高品質データセット（特に動画に重点）と、4段階の事前トレーニングと2段階の後処理を含む革新的なトレーニング手法に基づいて開発されました。

- 特に注目すべき革新は「思考」「非思考」「自動思考」「画像付き思考」「高品質動画データ」を含む5モードの「コールドスタート」データミックスで、モデルに推論のタイミングと方法を教えています。

- Keye-VLは公開動画ベンチマークで最先端の結果を達成し、一般的な画像ベースのタスクでも高い競争力を維持しており、実世界の短編動画シナリオ向けの新ベンチマークKC-MMBenchも開発・公開しています。

> **Huggingface Daily Papers** (https://arxiv.org/abs/2507.01949): Kwaiが開発した多言語・マルチモーダルモデルKeye-VLは、中国語・英語両言語で画像理解能力を強化。7Bパラメータながら、画像キャプション生成でCLIP-VITやBLIPを上回る精度を実現

## 5. AnthropicがAI技術の新展開を発表

- Anthropic社のCEOダリオ・アモデイ氏は5月下旬、AIによって5年以内に新卒レベルの仕事の半分が消滅し、米国の失業率が20%に達する可能性があると警告しました。

- アモデイ氏の発言は、AIによる雇用への影響という機微な話題に一石を投じるものでしたが、このような労働市場の大規模な変化を予測する声は彼だけではありません。

- 企業アメリカにおいて、AIが雇用市場に与える影響を予測することが新たな競争的スポーツのようになっていることが示唆されています。

> **TechCrunch** (https://techcrunch.com/2025/07/02/ai-job-predictions-become-corporate-americas-newest-competitive-sport/): 米大手企業がAI人材需要予測を競争化、McKinseyは2030年までに1200万人の雇用創出、Googleは全従業員の60%がAIツール活用と主張

## 6. New RelicがAIエージェントのROI測定手法を公開、可観測性技術で成果を数値化

- New RelicのAshan Willyが、AIエージェントシステムの計測方法について講演し、測定可能なROIを実現するための取り組みについて説明しました。

- AIエージェントエコシステムにおいて「可観測性(observability)」が重要な役割を果たすことが強調され、その必要性が議論されました。

- Transform 2025イベントにおいて、エージェント型AIの最大活用に向けた戦略が共有され、具体的な成果測定の手法が紹介されました。

> **VentureBeat AI** (https://venturebeat.com/ai/transform-2025-why-observability-is-critical-for-ai-agent-ecosystems/): 2025年に向けたAIエージェント生態系では。システム全体の可視化が障害検知・性能最適化の鍵。

## 7. OpenAI、Robinhoodの『OpenAIトークン』販売に警告 株式誤認の懸念表明

- OpenAIは、Robinhoodが販売している「OpenAIトークン」が一般消費者にOpenAIの株式や持分を与えるものではないことを明確に表明しました。

- Robinhoodの「OpenAIトークン」販売に対して、OpenAIが公式に懸念を示し、誤解を招く可能性のある表現に対して警告を発しています。

- この声明は、投資プラットフォームが提供する暗号資産や金融商品の表示方法について、テクノロジー企業が自社ブランドの誤用に敏感になっていることを示しています。

> **TechCrunch** (https://techcrunch.com/2025/07/02/openai-condemns-robinhoods-openai-tokens/): OpenAIが証券取引アプリRobinhoodの「OpenAIトークン」に対し商標権侵害で法的措置を検討。ユーザーを混乱させる偽暗号資産であり、OpenAIは暗号通貨市場に参入していないと強く否定。

---

## Lawrence's Insights

*※ここにLawrenceさんの手入力コメントを追加してください*

---
