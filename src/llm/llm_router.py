"""
LLM Router for handling multiple LLM providers with fallback support.
"""
import asyncio
import time
import logging
import re
from typing import Optional, Dict, Any, List
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from src.models.schemas import SummaryOutput, ProcessedArticle
from src.config.settings import get_settings

# Configure logging
logger = logging.getLogger(__name__)

class LLMRouter:
    """Router for managing multiple LLM providers with fallback support."""
    
    def __init__(self):
        """Initialize the LLM router with client configurations."""
        self.settings = get_settings()
        self.primary_models = [self.settings.llm.primary_model]
        self.fallback_models = [self.settings.llm.fallback_model, self.settings.llm.final_fallback_model]
        self.retry_delay = self.settings.llm.retry_delay
        self.timeout = self.settings.llm.timeout
        
        # Initialize clients lazily
        self._clients: Dict[str, BaseChatModel] = {}
        
        logger.info("LLM Router initialized with primary models: %s, fallback models: %s", 
                   self.primary_models, self.fallback_models)
    
    def _create_gemini_client(self) -> ChatGoogleGenerativeAI:
        """Create Gemini client with optimized settings."""
        api_key = self.settings.llm.gemini_api_key
        
        # Debug logging for API key
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is not set")
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        # Validate API key format
        if not api_key.startswith("AIzaSy") or len(api_key) < 30:
            logger.error("GEMINI_API_KEY appears to be invalid (wrong format or too short)")
            logger.debug("API key format: starts_with_AIzaSy=%s, length=%d", 
                        api_key.startswith("AIzaSy"), len(api_key))
            raise ValueError("GEMINI_API_KEY appears to be invalid")
        
        logger.info("Creating Gemini client with API key: %s...", api_key[:12])
        
        return ChatGoogleGenerativeAI(
            model=self.primary_models[0],  # コスト重視の 2.5 Flash に変更
            google_api_key=api_key,
            temperature=0.1,  # Reduced for consistency
            max_tokens=2048,
            timeout=self.timeout,
            max_retries=2
            # Note: removed thinking-related and response_format parameters as they're not supported by LangChain ChatGoogleGenerativeAI
        )
    
    def _create_claude_client(self) -> ChatAnthropic:
        """Create Claude client."""
        api_key = self.settings.llm.claude_api_key
        
        if not api_key:
            logger.error("ANTHROPIC_API_KEY environment variable is not set")
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        
        # Validate API key format
        if not api_key.startswith("sk-ant-") or len(api_key) < 50:
            logger.error("ANTHROPIC_API_KEY appears to be invalid (wrong format or too short)")
            logger.debug("API key format: starts_with_sk-ant=%s, length=%d", 
                        api_key.startswith("sk-ant-"), len(api_key))
            raise ValueError("ANTHROPIC_API_KEY appears to be invalid")
        
        logger.info("Creating Claude client with API key: %s...", api_key[:20])
        
        return ChatAnthropic(
            model="claude-3-7-sonnet-20250219",
            anthropic_api_key=api_key,
            temperature=0.3,
            max_tokens=2048,
            timeout=self.timeout
        )
    
    def _create_openai_client(self) -> ChatOpenAI:
        """Create OpenAI client."""
        api_key = self.settings.llm.openai_api_key
        
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable is not set")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Validate API key format (support both sk-proj- and sk- prefixes)
        if not (api_key.startswith("sk-proj-") or api_key.startswith("sk-")) or len(api_key) < 40:
            logger.error("OPENAI_API_KEY appears to be invalid (wrong format or too short)")
            logger.debug("API key format: starts_with_sk=%s, length=%d", 
                        api_key.startswith("sk-"), len(api_key))
            raise ValueError("OPENAI_API_KEY appears to be invalid")
        
        logger.info("Creating OpenAI client with API key: %s...", api_key[:20])
        
        return ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=api_key,
            temperature=0.3,
            max_tokens=2048,
            timeout=self.timeout
        )
    
    def _get_client(self, model_name: str) -> BaseChatModel:
        """Get or create a client for the specified model."""
        if model_name not in self._clients:
            if "gemini" in model_name:
                self._clients[model_name] = self._create_gemini_client()
            elif "claude" in model_name:
                self._clients[model_name] = self._create_claude_client()
            elif "gpt" in model_name:
                self._clients[model_name] = self._create_openai_client()
            else:
                raise ValueError(f"Unsupported model: {model_name}")
        
        return self._clients[model_name]
    
    async def generate_summary(
        self,
        article_title: str,
        article_content: str,
        article_url: str,
        source_name: str,
        max_retries: Optional[int] = None
    ) -> SummaryOutput:
        """
        Generate summary using primary model with fallback support.
        
        Args:
            article_title: Title of the article
            article_content: Content of the article
            article_url: URL of the article
            source_name: Name of the source
            max_retries: Maximum retries for primary model (default: 3)
        
        Returns:
            SummaryOutput: Generated summary with metadata
        """
        if max_retries is None:
            max_retries = 3
        
        # Prepare prompts
        system_prompt = self._get_summary_system_prompt()
        user_prompt = self._get_summary_user_prompt(
            article_title, article_content, article_url, source_name
        )
        
        last_error: Optional[Exception] = None
        primary_model = self.primary_models[0]
        fallback_models = self.fallback_models
        
        logger.info(
            "Attempting summary generation with model: %s, article: %s",
            primary_model,
            article_title[:50] + "..."
        )
        
        # Try primary model with retries
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                # Get client
                client = self._get_client(primary_model)
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", user_prompt),
                ])
                
                formatted_prompt = prompt.format_messages(
                    記事タイトル=article_title,
                    記事URL=article_url,
                    内容=article_content,
                    ソース名=source_name
                )
                
                response = await self._ainvoke_json(client, formatted_prompt, primary_model)
                
                # Log raw response for debugging
                logger.debug("RAW_RESP (model=%s): %s", primary_model, response.content[:500] if hasattr(response, "content") else str(response)[:500])
                logger.error("FULL RAW RESPONSE: %s", repr(response.content))
                
                # Use unified extraction method
                summary = self._extract_summary_from_response(response.content, primary_model)
                if summary:
                    processing_time = time.time() - start_time
                    estimated_cost = self._estimate_cost(primary_model, user_prompt, response.content)
                    
                    logger.info(
                        "Primary model summary successful - model: %s, attempt: %d, time: %.2fs, cost: $%.4f",
                        primary_model, attempt + 1, processing_time, estimated_cost
                    )
                    return summary
                
            except Exception as e:
                last_error = e
                processing_time = time.time() - start_time
                
                # Log detailed error information
                logger.warning(
                    "Summary generation attempt failed - model: %s, attempt: %d, error: %s (%s), time: %.2fs",
                    primary_model,
                    attempt + 1,
                    str(e),
                    type(e).__name__,
                    processing_time
                )
                logger.error("Full exception details:", exc_info=True)
                
                # Log response content for debugging if available
                if 'response' in locals() and hasattr(response, 'content'):
                    logger.debug(
                        "Response content: %s",
                        response.content[:500] if response.content else "None"
                    )
                    
                    # Wait before retry
                    if attempt < max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        # Try fallback models (1 attempt each)
        for fallback_model in fallback_models:
            try:
                result = await self._try_single_model(
                    fallback_model, article_title, article_content, article_url, source_name
                )
                if result:
                    return result
            except Exception as e:
                last_error = e
                logger.warning(
                    "Fallback summary generation failed - model: %s, error: %s",
                    fallback_model, str(e)
                )
        
        # All models failed, create fallback summary
        logger.error(
            "All LLM models failed, creating fallback summary - last_error: %s, article: %s",
            str(last_error),
            article_title
        )
        
        return self._create_fallback_summary(
            article_title, article_content, str(last_error)
        )
    
    async def _try_single_model(
        self, 
        model_name: str, 
        article_title: str, 
        article_content: str, 
        article_url: str, 
        source_name: str
    ) -> Optional[SummaryOutput]:
        """Try generating summary with a single model (helper method to reduce duplication)."""
        start_time = time.time()
        
        logger.info(
            "Attempting summary generation - model: %s, article: %s",
            model_name, article_title[:50] + "..."
        )
        
        # Get client
        client = self._get_client(model_name)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_summary_system_prompt()),
            ("human", self._get_summary_user_prompt(
                article_title, article_content, article_url, source_name
            )),
        ])
        
        formatted_prompt = prompt.format_messages()
        response = await self._ainvoke_json(client, formatted_prompt, model_name)
        
        # Parse response using existing extraction methods
        summary = self._extract_summary_from_response(response.content, model_name)
        if not summary:
            return None
            
        # Validate summary
        self._validate_summary(summary)
        
        # Add metadata
        summary.model_used = model_name
        processing_time = time.time() - start_time
        estimated_cost = self._estimate_cost(
            model_name, 
            self._get_summary_user_prompt(article_title, article_content, article_url, source_name), 
            response.content
        )
        
        logger.info(
            "Summary generation successful - model: %s, time: %.2fs, cost: $%.4f, confidence: %.2f",
            model_name, processing_time, estimated_cost, summary.confidence_score
        )
        
        return summary
    
    def _extract_summary_from_response(self, content: str, model_name: str) -> Optional[SummaryOutput]:
        """Extract SummaryOutput from LLM response content."""
        if not content:
            return None
            
        content = content.strip()
        
        # Try to extract JSON from various formats
        import json
        json_content = None
        
        # Method 1: Direct JSON parsing
        try:
            json_content = json.loads(content)
        except:
            pass
        
        # Method 2: Extract from markdown code blocks
        if json_content is None:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                try:
                    json_content = json.loads(json_match.group(1))
                except:
                    pass
        
        # Method 3: Find JSON object in text
        if json_content is None:
            json_match = re.search(r'\{[^{}]*"summary_points"[^{}]*\[[^\]]*\][^{}]*\}', content, re.DOTALL)
            if json_match:
                try:
                    json_content = json.loads(json_match.group(0))
                except:
                    pass
        
        # Method 4: Extract bullet list and convert to JSON
        if json_content is None:
            bullet_lines = re.findall(r'^[\-*•・\u2022]\s*(.+)', content, re.MULTILINE)
            if len(bullet_lines) >= 3:
                json_content = {"summary_points": bullet_lines[:4]}
        
        # Method 5: Extract meaningful sentences
        if json_content is None:
            sentences = re.split(r'[。.!?]', content)
            meaningful_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if (len(sentence) >= 30 and 
                    not any(word in sentence.lower() for word in [
                        "申し訳", "すみません", "sorry", "i apologize", "i cannot",
                        "以下に", "要約します", "まとめると", "について説明", "json", "format"
                    ])):
                    meaningful_sentences.append(sentence)
            
            if len(meaningful_sentences) >= 3:
                json_content = {"summary_points": meaningful_sentences[:4]}
        
        # Try creating SummaryOutput
        if json_content:
            try:
                return SummaryOutput(**json_content)
            except Exception as e:
                logger.warning(f"Pydantic validation failed: {e}, using text parsing")
        
        # Fallback to text parsing
        return self._parse_text_to_summary(content, model_name)
    
    def _get_summary_system_prompt(self) -> str:
        """Get system prompt for summary generation."""
        
        return """あなたは、日本のテクノロジー業界に精通した、高品質なAIニュースの専門編集者です。提供された記事から、読者にとって価値のある、具体的で詳細な日本語の要約を作成してください。

# 厳守すべき指示
- **出力形式**: 必ず指定されたJSON形式で、3〜4個の箇条書きポイントを生成してください。箇条書き以外のテキスト（挨拶、前置き、後書きなど）は一切含めないでください。
- **箇条書きの品質**: 各ポイントは、80文字以上120文字以内で（PRD厳守）、記事の核心（誰が、何をした、結果どうなった）を **具体的に** 記述してください。必ず数値、企業名、製品名、技術名を含めて、読者が記事の詳細内容を理解できるようにしてください。
- **具体的事実の必須抽出**: 各ポイントは必ず「○○社が」「△△%向上」「□□年から」等の具体的事実を含むこと。発表内容の詳細（機能名、性能数値、時期、対象業界等）を必ず記載してください。
- **具体性の強制要求**: 曖昧で一般的な表現は完全禁止。「AI技術の進歩」ではなく「GPT-4oの推論能力が50%向上」のように必ず具体的に記述してください。
- **文体**: 全ての文章は、です・ます調（敬体）で統一してください。
- **厳格禁止事項**: 以下の表現は絶対に使用禁止
  - 冗長表現: 「この記事では〜」「〜と述べられています」「記事の著者は」「〜によると」「〜について言及」「〜について触れて」
  - 否定的表現: 「断片的で」「不明確」「情報が少ない」「詳細は不明」「具体的な説明はない」
  - 個人名言及: 「kzzzm氏」「〜さん」「〜による」等の個人名（企業・製品名は除く）
  - メタ表現: 「記事の内容」「提供された情報」「上記の〜」「以下に〜」「記事によると」
  - **凡庸表現**: 「AIの活用が進む」「技術が発展」「新しい取り組み」「さらなる発展」「議論が活発化」「包括的な枠組み」「重要な進展」「新展開」「動向」等の非具体的表現

# 出力JSONスキーマ
{{
  "summary_points": [
    "箇条書きポイント1 (80〜120文字・簡潔に)",
    "箇条書きポイント2 (80〜120文字・簡潔に)",
    "箇条書きポイント3 (80〜120文字・簡潔に)",
    "箇条書きポイント4 (任意、必要であれば)"
  ],
  "confidence_score": "要約の自信度を0.0から1.0の数値で示す (例: 0.9)",
  "source_reliability": "情報源の信頼性を 'high', 'medium', 'low' のいずれかで示す"
}}

# 具体的な高品質の出力例（凡庸な表現との対比）
{{
  "summary_points": [
    "Sakana AIがTreeQuestアルゴリズムを開発、複数LLMの協調により単体比30%の性能向上を実現しました。",
    "モンテカルロ木探索とマルチエージェント技術を組み合わせ、複雑な推論タスクを階層的に分解処理します。",
    "Google DeepMindの研究チームとの共同検証で、数学的問題解決精度が従来手法の1.3倍に向上しました。",
    "2025年Q2から企業向けAPIの提供開始、金融・医療分野での実証実験も同時並行で進める予定です。"
  ],
  "confidence_score": 0.95,
  "source_reliability": "high"
}}

# 悪い例（凡庸で避けるべき表現）
❌ "AI技術が進歩し、新たな可能性が広がっています。"
❌ "企業がAIを活用した取り組みを強化しています。"
❌ "技術の発展により、さらなる改善が期待されます。"
❌ "AIエージェントアーキテクチャの進化の議論が活発化する中で"
❌ "包括的な枠組みとして設計されており"
❌ "重要な進展が発表"
❌ "新たな展開を象徴しています"

# 良い例（具体的で情報価値の高い表現）
✅ "OpenAIがGPT-4oの推論能力を50%向上、エンタープライズAPI提供を月内開始。"
✅ "Anthropic Claudeの文書解析精度が3倍改善、法務業界で実証実験開始。"
✅ "GoogleのGemini ProがYouTube動画自動要約機能を実装、処理速度2倍向上。"

上記指示を厳守し、記事内容に基づいたJSONを生成してください。
"""
    
    def _get_summary_user_prompt(
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

    # ------------------------------------------------------------------
    # Internal helper: async invoke that returns raw response
    # ------------------------------------------------------------------
    async def _ainvoke_json(self, client: BaseChatModel, messages, model_name: str):
        """Wrapper around `client.ainvoke` to standardise error handling.

        Some LangChain chat model clients return a ChatMessage; others return
        a wrapper object. We keep the result as-is so that callers can access
        `.content` safely. Any networking or API error will be propagated to
        the caller and handled by the retry logic upstream.
        """
        try:
            response = await client.ainvoke(messages)
            return response
        except Exception as e:  # noqa: BLE001
            logger.warning("ainvoke failed (model=%s): %s", model_name, e)
            raise

    # ------------------------------------------------------------------
    # Fallback summary generator (all LLM calls exhausted)
    # ------------------------------------------------------------------
    def _create_fallback_summary(self, article_title: str, article_content: str, last_error: str) -> SummaryOutput:
        """Create a minimal but valid SummaryOutput when all LLMs fail.

        Parameters
        ----------
        article_title : str
            Title of the article (used as first bullet point)
        article_content : str
            Raw article text – first 100 characters will be truncated.
        """
        truncated = (article_content[:100] + "...") if article_content else "内容取得に失敗しました。"
        bullets = [
            f"【速報】{article_title}",
            truncated,
            f"※自動要約に失敗したため、元記事をご確認ください。エラー: {last_error}"
        ]
        return SummaryOutput(
            summary_points=bullets,
            confidence_score=0.0,
            source_reliability="low"
        )
    
    def _validate_summary(self, summary: SummaryOutput) -> None:
        """Lightweight sanity check for SummaryOutput produced via text parsing.

        Raises
        ------
        ValueError
            If the summary does not satisfy basic quality gates.
        """
        if not summary or not summary.summary_points:
            raise ValueError("Summary has no points")
        if not (1 <= len(summary.summary_points) <= 6):
            raise ValueError("Unexpected number of summary points")

        # Ensure each summary point is substantial (>=30 文字／characters)
        for pt in summary.summary_points:
            if len(pt.strip()) < 30:
                raise ValueError("Summary point too short (<30 chars)")

    def _estimate_cost(self, model_name: str, prompt: str, response_content: str) -> float:
        """Very coarse cost estimation based on token count heuristics.

        Note: This is *not* an accurate billing estimator – it is only used for
        logging／monitoring. We approximate tokens ≈ characters / 4 and apply
        publicly-known $/1K‐token rates as of 2025-06 for major models. If the
        model is unknown, we return 0.0 to avoid crashing.
        """
        # Fallback safe-guard
        if not prompt or not response_content:
            return 0.0

        # Rough token count (characters / 4)
        prompt_tokens = max(1, len(prompt) // 4)
        response_tokens = max(1, len(response_content) // 4)
        total_tokens = prompt_tokens + response_tokens

        # USD per 1K tokens (approx.)
        rate_lookup = {
            "gemini-2.5-flash": 0.0005,   # hypothetical
            "claude-3-7-sonnet-20250219": 0.0008,
            "gpt-4o-mini": 0.0006,
        }
        rate = rate_lookup.get(model_name, 0.0)
        return round(total_tokens / 1000 * rate, 4)

    def _parse_text_to_summary(self, content: str, model_name: str = "unknown") -> SummaryOutput:
        """Parse LLM text response to SummaryOutput when JSON parsing fails.
        
        This method extracts summary points from free-form text responses.
        """
        if not content or not content.strip():
            raise ValueError("Empty content provided for text parsing")
        
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        summary_points = []
        
        # Extract bullet points or numbered items
        for line in lines:
            # Skip common headers/footers
            if any(skip in line.lower() for skip in ['要約', 'summary', '以下', '上記']):
                continue
                
            # Look for bullet points or numbered items
            if re.match(r'^[-*•]\s*', line) or re.match(r'^\d+\.\s*', line):
                # Remove bullet/number prefix
                clean_line = re.sub(r'^[-*•]\s*', '', line)
                clean_line = re.sub(r'^\d+\.\s*', '', clean_line)
                if len(clean_line) > 15:  # Substantial content
                    summary_points.append(clean_line)
            elif len(line) > 30 and '。' in line:
                # Treat longer sentences as summary points
                summary_points.append(line)
        
        # If no structured points found, split by sentences
        if not summary_points:
            sentences = re.split(r'[。.!?]', content)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20:
                    summary_points.append(sentence + '。')
        
        # Ensure we have at least some content
        if not summary_points:
            summary_points = [f"記事の要約：{content[:100]}..." if len(content) > 100 else content]
        
        # Limit to reasonable number of points
        summary_points = summary_points[:5]
        
        return SummaryOutput(
            summary_points=summary_points,
            confidence_score=0.3,  # Lower confidence for text parsing
            source_reliability="medium",
            model_used=model_name
        )

    async def generate_simple_text(
        self,
        prompt: str,
        max_tokens: int = 250,  # Reduced from 300 for faster processing (Lawrence's requirement)
        temperature: float = 0.2,
        max_retries: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate simple text using the primary model with fallback support.
        
        Args:
            prompt: The text prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            max_retries: Maximum retries for primary model (default: 2)
        
        Returns:
            Generated text or None if all models fail
        """
        if max_retries is None:
            max_retries = 2
        
        last_error: Optional[Exception] = None
        primary_model = self.primary_models[0]
        fallback_models = self.fallback_models
        
        logger.info(
            "Attempting simple text generation with model: %s",
            primary_model
        )
        
        # Try primary model with retries
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                # Get client
                client = self._get_client(primary_model)
                
                prompt_template = ChatPromptTemplate.from_messages([
                    ("human", prompt),
                ])
                
                formatted_prompt = prompt_template.format_messages()
                
                response = await self._ainvoke_json(client, formatted_prompt, primary_model)
                
                processing_time = time.time() - start_time
                
                logger.info(
                    "Simple text generation successful - model: %s, attempt: %d, time: %.2fs",
                    primary_model,
                    attempt + 1,
                    processing_time
                )
                
                return response.content.strip() if hasattr(response, 'content') else str(response).strip()
                
            except Exception as e:
                last_error = e
                processing_time = time.time() - start_time
                
                logger.warning(
                    "Simple text generation attempt failed - model: %s, attempt: %d, error: %s, time: %.2fs",
                    primary_model,
                    attempt + 1,
                    str(e),
                    processing_time
                )
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        # Try fallback models (1 attempt each)
        for fallback_model in fallback_models:
            logger.info(
                "Attempting fallback simple text generation - model: %s",
                fallback_model
            )
            
            try:
                start_time = time.time()
                
                client = self._get_client(fallback_model)
                
                prompt_template = ChatPromptTemplate.from_messages([
                    ("human", prompt),
                ])
                
                formatted_prompt = prompt_template.format_messages()
                
                response = await self._ainvoke_json(client, formatted_prompt, fallback_model)
                
                processing_time = time.time() - start_time
                
                logger.info(
                    "Fallback simple text generation successful - model: %s, time: %.2fs",
                    fallback_model,
                    processing_time
                )
                
                return response.content.strip() if hasattr(response, 'content') else str(response).strip()
                
            except Exception as e:
                last_error = e
                processing_time = time.time() - start_time
                
                logger.warning(
                    "Fallback simple text generation failed - model: %s, error: %s, time: %.2fs",
                    fallback_model,
                    str(e),
                    processing_time
                )
        
        # All models failed
        logger.error(
            "All LLM models failed for simple text generation - last_error: %s",
            str(last_error)
        )
        
        return None
    
    async def generate_citation_based_summary(
        self,
        article_title: str,
        article_content: str,
        article_url: str,
        source_name: str,
        citations: List[Dict[str, str]] = None,
        max_retries: Optional[int] = None
    ) -> SummaryOutput:
        """
        Generate summary using citation information (PRD F-15 compliance).
        
        Args:
            article_title: Title of the main article
            article_content: Content of the main article
            article_url: URL of the main article
            source_name: Name of the main source
            citations: List of citation dicts with 'title', 'url', 'summary' keys
            max_retries: Maximum retries for primary model (default: 3)
        
        Returns:
            SummaryOutput: Generated summary incorporating citation information
        """
        if max_retries is None:
            max_retries = 3
        
        # Prepare prompts with citation context
        system_prompt = self._get_citation_based_system_prompt()
        user_prompt = self._get_citation_based_user_prompt(
            article_title, article_content, article_url, source_name, citations or []
        )
        
        last_error: Optional[Exception] = None
        primary_model = self.primary_models[0]
        fallback_models = self.fallback_models
        
        logger.info(
            "Attempting citation-based summary generation with model: %s, article: %s, citations: %d",
            primary_model,
            article_title[:50] + "...",
            len(citations) if citations else 0
        )
        
        # Try primary model with retries
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                # Get client
                client = self._get_client(primary_model)
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", user_prompt),
                ])
                
                formatted_prompt = prompt.format_messages(
                    記事タイトル=article_title,
                    記事URL=article_url,
                    内容=article_content,
                    ソース名=source_name
                )
                
                response = await self._ainvoke_json(client, formatted_prompt, primary_model)
                
                # Log raw response for debugging
                logger.debug("CITATION_BASED_RAW_RESP (model=%s): %s", primary_model, response.content[:500] if hasattr(response, "content") else str(response)[:500])
                
                # Parse structured output with robust JSON extraction
                content = response.content.strip()
                
                # Try to extract JSON from various formats (same as original method)
                import json
                json_content = None
                
                # Method 1: Direct JSON parsing
                try:
                    json_content = json.loads(content)
                except:
                    pass
                
                # Method 2: Extract from markdown code blocks
                if json_content is None:
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        try:
                            json_content = json.loads(json_match.group(1))
                        except:
                            pass
                
                # Method 3: Find JSON object in text
                if json_content is None:
                    json_match = re.search(r'\{[^{}]*"summary_points"[^{}]*\[[^\]]*\][^{}]*\}', content, re.DOTALL)
                    if json_match:
                        try:
                            json_content = json.loads(json_match.group(0))
                        except:
                            pass
                
                # Method 4: Clean and try again
                if json_content is None:
                    cleaned_content = content
                    for prefix in ["```json", "```"]:
                        if cleaned_content.startswith(prefix):
                            cleaned_content = cleaned_content[len(prefix):]
                    for suffix in ["```"]:
                        if cleaned_content.endswith(suffix):
                            cleaned_content = cleaned_content[:-len(suffix)]
                    cleaned_content = cleaned_content.strip()
                    try:
                        json_content = json.loads(cleaned_content)
                    except:
                        pass
                
                # Method 5: Extract bullet list and convert to JSON
                if json_content is None:
                    bullet_lines = re.findall(r'^[\-*•・\u2022]\s*(.+)', content, re.MULTILINE)
                    if len(bullet_lines) >= 3:
                        json_content = {
                            "summary_points": bullet_lines[:4]
                        }
                
                # Method 6: Extract from pure text and convert to bullet points
                if json_content is None:
                    logger.debug("Citation-based Method 6: Pure text to bullet conversion")
                    sentences = re.split(r'[。.!?]', content)
                    meaningful_sentences = []
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if (len(sentence) >= 30 and 
                            not any(word in sentence.lower() for word in [
                                "申し訳", "すみません", "sorry", "i apologize", "i cannot",
                                "以下に", "要約します", "まとめると", "について説明", "json", "format"
                            ])):
                            meaningful_sentences.append(sentence)
                    
                    if len(meaningful_sentences) >= 3:
                        json_content = {
                            "summary_points": meaningful_sentences[:4]
                        }
                        logger.debug("Citation-based Method 6 successful: Created %d bullet points from text", 
                                   len(json_content["summary_points"]))
                
                # If we have JSON content, validate it with Pydantic
                if json_content:
                    try:
                        summary = SummaryOutput(**json_content)
                        summary.model_used = primary_model
                        processing_time = time.time() - start_time
                        estimated_cost = self._estimate_cost(primary_model, user_prompt, response.content)
                        
                        logger.info(
                            "Citation-based summary generation successful - model: %s, attempt: %d, time: %.2fs, cost: $%.4f",
                            primary_model, attempt + 1, processing_time, estimated_cost
                        )
                        return summary
                        
                    except Exception as e:
                        logger.warning(f"Citation-based Pydantic validation failed: {e}, using direct text parsing")
                        summary = self._parse_text_to_summary(content, model_name=primary_model)
                else:
                    logger.debug("Citation-based: No JSON found, parsing as text directly")
                    summary = self._parse_text_to_summary(content, model_name=primary_model)
                    
                # Validate summary
                self._validate_summary(summary)
                
                # Add metadata
                summary.model_used = primary_model
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Estimate cost
                estimated_cost = self._estimate_cost(
                primary_model, user_prompt, response.content
                )
                
                logger.info(
                "Citation-based summary generation successful - model: %s, attempt: %d, time: %.2fs, cost: $%.4f, confidence: %.2f",
                primary_model,
                attempt + 1,
                processing_time,
                estimated_cost,
                summary.confidence_score
                )
                
                return summary
                
            except Exception as e:
                last_error = e
                processing_time = time.time() - start_time
                
                logger.warning(
                    "Citation-based summary generation attempt failed - model: %s, attempt: %d, error: %s, time: %.2fs",
                    primary_model,
                    attempt + 1,
                    str(e),
                    processing_time
                )
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        # Primary model failed, try fallback models (1 attempt each)
        for fallback_model in fallback_models:
            logger.info(
                "Attempting fallback citation-based summary generation - model: %s",
                fallback_model
            )
            
            try:
                start_time = time.time()
                
                client = self._get_client(fallback_model)
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", self._get_citation_based_system_prompt()),
                    ("human", self._get_citation_based_user_prompt(
                        article_title, article_content, article_url, source_name, citations or []
                    )),
                ])
                
                formatted_prompt = prompt.format_messages()
                
                response = await self._ainvoke_json(client, formatted_prompt, fallback_model)
                
                # Parse structured output (same as primary model)
                content = response.content.strip()
                
                # Try to extract JSON (same methods as primary)
                import json
                json_content = None
                
                try:
                    json_content = json.loads(content)
                except:
                    pass
                
                if json_content is None:
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        try:
                            json_content = json.loads(json_match.group(1))
                        except:
                            pass
                
                if json_content:
                    try:
                        summary = SummaryOutput(**json_content)
                    except Exception as e:
                        summary = self._parse_text_to_summary(content)
                else:
                    summary = self._parse_text_to_summary(content)
                
                # Validate summary
                self._validate_summary(summary)
                
                # Add metadata
                summary.model_used = fallback_model
                
                processing_time = time.time() - start_time
                estimated_cost = self._estimate_cost(
                    fallback_model, self._get_citation_based_user_prompt(
                        article_title, article_content, article_url, source_name, citations or []
                    ), response.content
                )
                
                logger.info(
                    "Fallback citation-based summary generation successful - model: %s, time: %.2fs, cost: $%.4f",
                    fallback_model,
                    processing_time,
                    estimated_cost
                )
                
                return summary
                
            except Exception as e:
                last_error = e
                processing_time = time.time() - start_time
                
                logger.warning(
                    "Fallback citation-based summary generation failed - model: %s, error: %s, time: %.2fs",
                    fallback_model,
                    str(e),
                    processing_time
                )
        
        # All models failed, create fallback summary
        logger.error(
            "All LLM models failed for citation-based summary, creating fallback summary - last_error: %s, article: %s",
            str(last_error),
            article_title
        )
        
        return self._create_fallback_summary(
            article_title, article_content, str(last_error)
        )
    
    def _get_citation_based_system_prompt(self) -> str:
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
- **厳格禁止事項**: 以下の表現は絶対に使用禁止
  - 冗長表現: 「この記事では〜」「〜と述べられています」「記事の著者は」「〜によると」「〜について言及」
  - 否定的表現: 「断片的で」「不明確」「情報が少ない」「詳細は不明」
  - 個人名言及: 「kzzzm氏」「〜さん」等の個人名（企業・製品名は除く）
  - メタ表現: 「記事の内容」「提供された情報」「上記の〜」
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
    
    def _get_citation_based_user_prompt(
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

上記のメイン記事と関連記事の引用情報を統合して、包括的な要約を生成してください。
引用情報を活用し、より深い洞察と価値を提供する要約にしてください。"""
    
    async def generate_japanese_title(
        self,
        article: ProcessedArticle,
        max_tokens: int = 100,
        temperature: float = 0.3
    ) -> Optional[str]:
        """
        Generate a Japanese title for an article using LLM.
    
    Args:
            article: ProcessedArticle object
            max_tokens: Maximum tokens for response
            temperature: Temperature for generation
    
    Returns:
            Japanese title string or None if generation fails
        """
        try:
            # Extract content from article
            summary_points = []
            if (hasattr(article, 'summarized_article') and 
                article.summarized_article and
                hasattr(article.summarized_article, 'summary') and 
                article.summarized_article.summary and
                hasattr(article.summarized_article.summary, 'summary_points')):
                summary_points = article.summarized_article.summary.summary_points
            
            original_title = ""
            if (hasattr(article, 'summarized_article') and
                article.summarized_article and
                hasattr(article.summarized_article, 'filtered_article') and
                article.summarized_article.filtered_article and
                hasattr(article.summarized_article.filtered_article, 'raw_article') and
                article.summarized_article.filtered_article.raw_article):
                original_title = article.summarized_article.filtered_article.raw_article.title
            
            if not summary_points:
                return None
            
            # Check if this is an UPDATE article
            is_update = getattr(article, 'is_update', False)
            update_context = ""
            if is_update:
                update_context = f"""

# 重要：この記事は続報/更新記事です
- 過去の関連記事に対する新しい展開・続報を示す内容です
- 見出しには「新展開」「続報」「更新」といった継続性を示す要素を含めてください
- 具体的な進展や変化を強調してください"""
            
            # Create a new, simpler prompt focused on summarizing the summary.
            prompt = f"""あなたはプロのニュース見出し編集者です。以下の記事要約から、読者の関心を引く魅力的で具体的な日本語見出しを生成してください。

# 記事要約
{chr(10).join(f'- {point}' for point in summary_points)}{update_context}

# 見出し作成要件
## 基本要件
- **文字数**: 25-55文字（目安：30-45文字が最適）
- **形式**: 体言止めまたは動詞で締める
- **具体性**: 企業名・製品名・数値を必ず含める
- **魅力**: 読者が「詳細を知りたい」と思う内容

## 必須要素（優先順位順）
1. **具体的な企業名・製品名**（例：OpenAI、ChatGPT-4o、Gemini Pro、DeepSWE、Agentica）
2. **具体的な動作・結果**（例：50%向上、月内開始、3倍拡大、42.2%達成、1000万ドル）
3. **技術・分野の明示**（例：推論能力、画像認識、音声合成、コーディング、強化学習）
4. **市場・ユーザーへの影響**（例：企業向け、一般向け、開発者向け、SOTA達成）

## 高品質見出しテンプレート
**企業名 + 製品/技術 + 具体的数値/成果 + 影響範囲**
- 「OpenAI、年間1000万ドル顧客へAIコンサル拡大、2025年6月までに120億ドル収益へ」
- 「AgenticaとTogether AI、DeepSWE-Previewが強化学習でコーディングSOTA、Pass@1 42.2%達成」
- 「Anthropic、Claude 3.5の文書解析精度を3倍改善、法務業界に本格展開」

## 絶対禁止事項
- **抽象的表現**: 「AI分野で新発表」「企業がAI活用」
- **助詞での終了**: 「〜は」「〜が」「〜を」
- **冗長な報告表現**: 「〜と発表しました」「〜と述べました」
- **一般的すぎる用語**: 単独の「AI」「技術」「サービス」

## 優秀な見出し例
✅ 「OpenAIがGPT-4oの推論能力を50%向上、企業向けAPIを月内開始」
✅ 「GoogleのGemini ProがYouTube動画の自動要約機能を実装」
✅ 「MetaがLlama 3.5をオープンソース公開、商用利用も完全無料化」
✅ 「AnthropicのClaude 3.5が文書解析精度を3倍改善、法務業界に本格展開」

## 続報記事の優秀な見出し例（UPDATE記事の場合）
✅ 「OpenAI ChatGPT Plus、新展開でAPIコスト30%削減を実現」
✅ 「Google Gemini Pro続報：マルチモーダル機能が予想超えの精度向上」
✅ 「Meta Llama 3.5更新版、推論速度が従来比2倍に大幅改善」
✅ 「Anthropic Claude最新アップデート、長文処理能力の制限を完全撤廃」

## 避けるべき悪い例
❌ 「AI分野で新たな発表」（抽象的、企業名なし）
❌ 「企業がAIを活用した新サービス」（具体性ゼロ）
❌ 「OpenAIが新機能を発表しました」（冗長、数値なし）
❌ 「LinkedInが導入したAIエージェントは」（助詞で終了）

# 生成する見出し（1つのみ）:
"""
            
            # Generate using simple text generation
            result = await self.generate_simple_text(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                max_retries=2
            )
            
            if result:
                # Clean up the result with improved multi-line handling (Lawrence's requirement)
                lines = [line.strip() for line in result.splitlines() if line.strip()]
                if lines:
                    # Take the last substantial line (YouTube title fix)
                    title = lines[-1]
                else:
                    title = result.strip()
                
                # Remove quotes and hash marks if present (fixes double hash mark issue)
                title = re.sub(r'^[#\s]*["\'「]|["\'」]+$', '', title).strip()
                title = re.sub(r'^#+\s*', '', title)  # Remove any remaining leading hash marks
                # Remove any remaining newlines
                title = title.replace('\n', ' ').strip()
                
                # Enhanced validation with quality scoring
                if 10 <= len(title) <= 60:
                    # Quality scoring system
                    quality_score = 0
                    rejection_reasons = []
                    
                    # 1. Check for specific content (企業名・製品名) - 拡張版
                    companies = ['OpenAI', 'Google', 'Meta', 'Microsoft', 'Anthropic', 'Apple', 'Amazon', 'Tesla', 'NVIDIA', 
                                'Agentica', 'Together AI', 'DeepMind', 'Hugging Face', 'TechCrunch', 'VentureBeat', 'WIRED',
                                'IEEE', 'NextWord', 'SemiAnalysis', 'Bay Area Times']
                    products = ['ChatGPT', 'GPT-4', 'Gemini', 'Claude', 'Llama', 'Copilot', 'Bard', 'DeepSWE', 'rLLM', 
                              'GRPO++', 'SWE-Bench', 'Qwen3', 'Cursor', 'RAG', 'LLM', 'SDK', 'API']
                    
                    has_company = any(company in title for company in companies)
                    has_product = any(product in title for product in products)
                    
                    if has_company or has_product:
                        quality_score += 3
                    else:
                        rejection_reasons.append("企業名・製品名なし")
                    
                    # 2. Check for numbers/metrics
                    has_numbers = bool(re.search(r'\d+[%倍件万円ドル]|[1-9]\d*[年月日]', title))
                    if has_numbers:
                        quality_score += 2
                    
                    # 3. Check for action verbs (not just passive reporting)
                    action_verbs = ['発表', '開始', '実装', '展開', '公開', '導入', '拡大', '改善', '向上', '開発']
                    has_action = any(verb in title for verb in action_verbs)
                    if has_action:
                        quality_score += 1
                    
                    # 4. Problematic patterns (immediate rejection) - 修正版
                    problematic_patterns = [
                        r'発表を発表',                  # Duplicate "発表を発表"
                        r'.*が.*が.*',                # Double particle "が" (fixed pattern)
                        r'^.{1,10}$',                 # Too short (under 10 chars)
                        r'^.{1,}を複数$',             # Incomplete "を複数"で終わる
                        r'^複数が.*',                  # Starts with "複数が"
                        r'^.{1,}を進行$',             # Incomplete "を進行"で終わる
                        r'^.{1,}に影響$',             # Incomplete "に影響"で終わる
                        r'^.{1,}が導入$',             # Incomplete "が導入"で終わる
                        r'^AIの最新動向$',            # Generic "AIの最新動向"
                        r'^.{1,}の動向$',             # Generic "〜の動向"
                        r'^.{1,}の発展$',             # Generic "〜の発展"
                        r'^AI分野.*$',                # Generic "AI分野"
                    ]
                    
                    # Check for problematic patterns
                    is_problematic = any(re.search(pattern, title) for pattern in problematic_patterns)
                    if is_problematic:
                        rejection_reasons.append("問題のある表現パターン")
                    
                    # Check for incomplete sentences ending with particles
                    particle_endings = ('は', 'が', 'を', 'に', 'で', 'と', 'から', 'まで', 'より', 'への')
                    ends_with_particle = title.endswith(particle_endings)
                    if ends_with_particle:
                        rejection_reasons.append("助詞での終了")
                    
                    # Check for verb endings that indicate incomplete reporting 
                    incomplete_verbs = ('と発表しました', 'と報告しました', 'と述べました', 'と語りました')
                    ends_with_incomplete_verb = title.endswith(incomplete_verbs)
                    if ends_with_incomplete_verb:
                        rejection_reasons.append("不完全な報告表現")
                    
                    # Final quality decision - 緩和版
                    min_quality_score = 2  # 緩和: 企業名/製品名があれば基本的にOK
                    
                    if quality_score >= min_quality_score and not rejection_reasons:
                        logger.info(f"High-quality title accepted (score: {quality_score}): {title}")
                        return title
                    else:
                        reasons_str = ", ".join(rejection_reasons) if rejection_reasons else "品質スコア不足"
                        logger.warning(f"Title rejected (score: {quality_score}, reasons: {reasons_str}): {title}")
                        
                    # Try to clean incomplete patterns
                    cleaned_title = title
                    
                    # Remove incomplete verb endings
                    for ending in incomplete_verbs:
                        if cleaned_title.endswith(ending):
                            cleaned_title = cleaned_title[:-len(ending)]
                    
                    # Remove particle endings and create complete phrase
                    for particle in particle_endings:
                        if cleaned_title.endswith(particle):
                            cleaned_title = cleaned_title[:-len(particle)]
                            # Add appropriate completion based on context
                            if any(word in cleaned_title for word in ['導入', '発表', '開発', '公開']):
                                cleaned_title += 'を実施'
                            elif any(word in cleaned_title for word in ['企業', 'AI', 'サービス']):
                                cleaned_title += 'が進化'
                            else:
                                cleaned_title += 'の動向'
                            break
                    
                    if 10 <= len(cleaned_title) <= 60 and not any(re.search(pattern, cleaned_title) for pattern in problematic_patterns):
                        logger.info(f"Cleaned and accepted title: {cleaned_title}")
                        return cleaned_title
                elif len(title) > 60:
                    # Smart truncation at sentence boundaries
                    truncated = title[:60]
                    # Find last complete word boundary
                    last_space = truncated.rfind(' ')
                    last_comma = truncated.rfind('、')
                    last_period = truncated.rfind('。')
                    
                    best_cut = max(last_space, last_comma, last_period)
                    if best_cut > 40:  # Only if we don't cut too much
                        return truncated[:best_cut]
                    else:
                        return truncated[:57] + "..."
                
                return None
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to generate Japanese title: {e}")
            return None

# Example usage (for testing)
async def main():
    """Test the LLM router."""