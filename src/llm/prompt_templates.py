"""
Prompt template management for various LLM operations.

This module contains all prompt templates used for different LLM operations
including summary generation, title generation, and citation-based processing.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PromptTemplates:
    """Manager for LLM prompt templates."""
    
    def __init__(self):
        """Initialize prompt templates."""
        logger.info("Prompt Templates initialized")
    
    def get_summary_system_prompt(self) -> str:
        """Get system prompt for summary generation."""
        return """AI記事を3-4個の箇条書きで日本語要約してください。

要件:
- JSON形式で出力: {{"summary_points": ["要約1", "要約2", "要約3"], "confidence_score": 0.9, "source_reliability": "high"}}
- 各要約80-120文字、企業名・数値を含む具体的内容
- です・ます調で統一
- 冗長表現（「〜と発表」「〜について」等）禁止

例:
{{
  "summary_points": [
    "OpenAIがGPT-4oの推論能力を50%向上、エンタープライズAPI提供を月内開始しました。",
    "新機能では複雑な数学問題の処理速度が従来の2倍に改善され、金融業界での実用化を目指します。",
    "開発費用は1億ドルで、2025年第2四半期からベータ版の提供を開始する予定です。"
  ],
  "confidence_score": 0.9,
  "source_reliability": "high"
}}
"""
    
    def get_summary_user_prompt(
        self,
        title: str,
        content: str,
        url: str,
        source: str
    ) -> str:
        """Generate user prompt for summary."""
        return f"""記事タイトル: {title}

記事内容:
{content[:2000]}

ソース: {source}
URL: {url}

上記の記事を要約してください。"""
    
    def get_citation_based_system_prompt(self) -> str:
        """
        Get system prompt for citation-based summary generation (PRD F-15 compliance).
        """
        return """あなたは、日本のテクノロジー業界に精通した、高品質なAIニュースの専門編集者です。

# 重要：引用情報を活用した要約生成 (PRD F-15準拠)
提供されたメイン記事と関連記事の引用情報を統合し、包括的で価値の高い日本語要約を作成してください。

# 厳守すべき指示
- **出力形式**: 必ず指定されたJSON形式で、3〜4個の箇条書きポイントを生成してください。
- **引用活用**: 関連記事の引用情報を要約に反映し、より深い洞察を提供してください。
- **箇条書きの品質**: 各ポイントは80文字以上120文字以内で、メイン記事と引用情報を統合した内容にしてください。
- **文体**: 全ての文章は、です・ます調（敬体）で統一してください。
- **日本語品質の重要要求**: 自然で流暢な日本語を使用し、機械翻訳的な不自然な表現を避けてください。文章の流れを重視し、読者が違和感なく読める文章を作成してください。
- **厳格禁止事項**: 以下の表現は絶対に使用禁止
  - 冗長表現: 「この記事では〜」「〜と述べられています」「記事の著者は」「〜によると」「〜について言及」
  - 否定的表現: 「断片的で」「不明確」「情報が少ない」「詳細は不明」
  - 個人名言及: 「kzzzm氏」「〜さん」等の個人名（企業・製品名は除く）
  - メタ表現: 「記事の内容」「提供された情報」「上記の〜」
  - 不自然な文構造: 「〜することが可能です」「〜という形で」「〜のような状況です」「〜に関しては」
  - 助詞の重複: 「〜にが」「〜をが」「〜でが」「〜とが」「〜からが」等の助詞重複パターン
- **自然な表現**: 直接的で具体的な事実を、人が読んで違和感のない自然で流暢な日本語で記述してください。

# 出力JSONスキーマ
{{
  "summary_points": [
    "箇条書きポイント1 (80〜120文字・引用情報を活用)",
    "箇条書きポイント2 (80〜120文字・統合的な洞察)",
    "箇条書きポイント3 (80〜120文字・具体的事実)",
    "箇条書きポイント4 (任意、必要であれば)"
  ],
  "confidence_score": "要約の自信度を0.0から1.0の数値で示す (例: 0.9)",
  "source_reliability": "情報源の信頼性を 'high', 'medium', 'low' のいずれかで示す"
}}

# 高品質な引用活用例
{{
  "summary_points": [
    "OpenAI社がGPT-5を正式発表、関連技術記事によると推論能力が前世代比50%向上しています。",
    "マルチモーダル機能を大幅強化し、複数のソースで動画コンテンツの理解・生成能力向上が確認されています。",
    "エンタープライズAPI提供は2025年Q3開始予定で、業界専門誌でも企業導入への期待が高まっています。",
    "医療・科学分野での活用推進により、関連研究機関との連携強化も同時発表されています。"
  ],
  "confidence_score": 0.95,
  "source_reliability": "high"
}}

上記指示を厳守し、メイン記事と引用情報を統合したJSONを生成してください。"""
    
    def get_citation_based_user_prompt(
        self,
        title: str,
        content: str,
        url: str,
        source: str,
        citations: List[Dict[str, str]]
    ) -> str:
        """
        Generate user prompt for citation-based summary (PRD F-15 compliance).
        """
        # Format citations for prompt
        citations_text = ""
        if citations:
            citations_text = "\n\n# 関連記事の引用情報\n"
            for i, citation in enumerate(citations[:3], 1):  # Limit to 3 citations per PRD
                citations_text += f"""
## 引用{i}
- タイトル: {citation.get('title', 'タイトル不明')}
- ソース: {citation.get('source_name', '不明')}
- 要約: {citation.get('japanese_summary', citation.get('summary', '要約なし'))}
- URL: {citation.get('url', '')}
"""

        return f"""# メイン記事
記事タイトル: {title}

記事内容:
{content[:2000]}

ソース: {source}
URL: {url}{citations_text}

上記のメイン記事と関連記事の引用情報を統合した要約を生成してください。"""
    
    def get_title_generation_prompt(
        self,
        summary_points: List[str],
        is_update: bool = False
    ) -> str:
        """Generate prompt for Japanese title generation."""
        update_context = ""
        if is_update:
            update_context = """

# 重要：この記事は続報/更新記事です
- 過去の関連記事に対する新しい展開・続報を示す内容です
- 見出しには「新展開」「続報」「更新」といった継続性を示す要素を含めてください
- 具体的な進展や変化を強調してください"""

        return f"""記事要約から日本語見出しを1つ作成。見出しのみ出力。

記事要約:
{chr(10).join(f'- {point}' for point in summary_points)}{update_context}

要件:
- 25-55文字
- 企業名・数値含む
- 体言止め/動詞止め
- 挨拶・説明文禁止

出力例: OpenAI、GPT-4o推論能力50%向上、企業API月内開始"""
    
    def get_simple_text_system_prompt(self) -> str:
        """Get system prompt for simple text generation."""
        return """あなたは正確で簡潔な日本語テキストを生成する専門AIアシスタントです。

# 重要指示
- ユーザーの要求に対して、必要な情報のみを簡潔に出力してください
- 余計な説明、挨拶、質問は一切含めないでください
- 指定された形式・文字数制限を厳密に守ってください
- 自然で読みやすい日本語を使用してください

# 禁止事項
- 「はい」「承知しました」等の挨拶
- 「以下に〜」「〜について説明します」等の説明文
- 「〜でしょうか」「〜と思います」等の曖昧な表現
- 不要な前置きや後置き

要求された内容のみを直接出力してください。"""
    
    def get_contextual_update_prompt(
        self,
        current_title: str,
        current_points: List[str],
        references_text: str,
        reasoning: str,
        past_links_text: str = ""
    ) -> str:
        """Generate prompt for contextual update summary generation."""
        return f"""以下の続報記事について、過去の関連記事の文脈を踏まえた包括的な日本語要約を生成してください。

【今回の記事】
タイトル: {current_title}
要点: {' / '.join(current_points)}

【過去の関連記事】
{references_text}

【文脈分析】
{reasoning}

【要件】
- 必ず4項目の箇条書きで作成
- 各項目150-200文字程度
- 過去の経緯を自然に織り込む
- 今回の新しい展開を明確に示す
- 「続報」「UPDATE」等の文言は使わない
- 具体的な変化や進展を強調

【出力形式】
- 過去の経緯を踏まえた現在の状況
- 今回発表された新しい要素や変化
- これまでとの比較や違い
- 今後への影響や展望{past_links_text}"""
    
    def get_available_templates(self) -> List[str]:
        """Get list of available prompt templates."""
        return [
            "summary_system",
            "summary_user", 
            "citation_based_system",
            "citation_based_user",
            "title_generation",
            "simple_text_system",
            "contextual_update"
        ]
    
    def validate_template_args(self, template_name: str, **kwargs) -> bool:
        """Validate arguments for a specific template."""
        required_args = {
            "summary_user": ["title", "content", "url", "source"],
            "citation_based_user": ["title", "content", "url", "source", "citations"],
            "title_generation": ["summary_points"],
            "contextual_update": ["current_title", "current_points", "references_text", "reasoning"]
        }
        
        if template_name in required_args:
            missing_args = set(required_args[template_name]) - set(kwargs.keys())
            if missing_args:
                logger.warning(f"Missing required arguments for {template_name}: {missing_args}")
                return False
        
        return True