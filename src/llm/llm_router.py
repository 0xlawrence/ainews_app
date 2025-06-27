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
from src.constants.settings import LLM_CONFIG

# Configure logging
logger = logging.getLogger(__name__)

class LLMRouter:
    """Router for managing multiple LLM providers with fallback support."""
    
    def __init__(self):
        """Initialize the LLM router with client configurations."""
        from src.constants.settings import LLM_CONFIG
        self.primary_models = LLM_CONFIG["primary_models"]
        self.fallback_models = ["claude-3-7-sonnet-20250219", "gpt-4o-mini"]
        self.retry_delay = 2.0
        self.timeout = 60
        
        # Initialize clients lazily
        self._clients: Dict[str, BaseChatModel] = {}
        
        logger.info("LLM Router initialized with primary models: %s, fallback models: %s", 
                   self.primary_models, self.fallback_models)
    
    def _create_gemini_client(self) -> ChatGoogleGenerativeAI:
        """Create Gemini client with optimized settings."""
        api_key = os.getenv("GEMINI_API_KEY")
        
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
            # Note: removed response_format as it's not supported by LangChain ChatGoogleGenerativeAI
        )
    
    def _create_claude_client(self) -> ChatAnthropic:
        """Create Claude client."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
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
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable is not set")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Validate API key format
        if not api_key.startswith("sk-proj-") or len(api_key) < 50:
            logger.error("OPENAI_API_KEY appears to be invalid (wrong format or too short)")
            logger.debug("API key format: starts_with_sk-proj=%s, length=%d", 
                        api_key.startswith("sk-proj-"), len(api_key))
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
                
                formatted_prompt = prompt.format_messages()
                
                response = await self._ainvoke_json(client, formatted_prompt, primary_model)
                
                # Log raw response for debugging
                logger.debug("RAW_RESP (model=%s): %s", primary_model, response.content[:500] if hasattr(response, "content") else str(response)[:500])
                logger.error("FULL RAW RESPONSE: %s", repr(response.content))
                
                # Parse structured output with robust JSON extraction
                content = response.content.strip()
                
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
                
                # Method 3: Find JSON object in text (improved for multiline)
                if json_content is None:
                    # Look for complete JSON objects with summary_points, handling newlines
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
                
                # Method 5 – Extract bullet list and convert to JSON
                if json_content is None:
                    bullet_lines = re.findall(r'^[\-*•・\u2022]\s*(.+)', content, re.MULTILINE)
                    if len(bullet_lines) >= 3:
                        json_content = {
                            "summary_points": bullet_lines[:4]
                        }
                
                # NEW: Method 6 – Extract from pure text and convert to bullet points
                if json_content is None:
                    logger.debug("Attempting Method 6: Pure text to bullet conversion")
                    
                    # Split text into sentences
                    sentences = re.split(r'[。.!?]', content)
                    # Filter out short sentences and clean them
                    meaningful_sentences = []
                    for sentence in sentences:
                        sentence = sentence.strip()
                        # Skip very short sentences, meta comments, or instruction text
                        if (len(sentence) >= 30 and 
                            not any(word in sentence.lower() for word in [
                                "申し訳", "すみません", "sorry", "i apologize", "i cannot",
                                "以下に", "要約します", "まとめると", "について説明", "json", "format"
                            ])):
                            meaningful_sentences.append(sentence)
                    
                    # Take first 3-4 meaningful sentences as bullet points
                    if len(meaningful_sentences) >= 3:
                        json_content = {
                            "summary_points": meaningful_sentences[:4]
                        }
                        logger.debug("Method 6 successful: Created %d bullet points from text", 
                                   len(json_content["summary_points"]))
                
                # If we have JSON content, validate it with Pydantic
                if json_content:
                    try:
                        summary = SummaryOutput(**json_content)
                        # Early success return - skip fallbacks (Lawrence's requirement)
                        summary.model_used = primary_model
                        processing_time = time.time() - start_time
                        estimated_cost = self._estimate_cost(primary_model, user_prompt, response.content)
                        
                        logger.info(
                            "Summary generation successful (early return) - model: %s, attempt: %d, time: %.2fs, cost: $%.4f",
                            primary_model, attempt + 1, processing_time, estimated_cost
                        )
                        return summary
                        
                    except Exception as e:
                        logger.warning(f"Pydantic validation failed: {e}, using direct text parsing")
                        logger.debug(f"JSON content was: {json_content}")
                        # Direct fallback to text parsing instead of problematic parser.parse()
                        summary = self._parse_text_to_summary(content, model_name=primary_model)
                else:
                    # Direct text parsing instead of parser.parse() which causes KeyError
                    logger.debug("No JSON found, parsing as text directly")
                    logger.debug(f"Raw content from LLM: {content[:200]}...")
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
                "Summary generation successful - model: %s, attempt: %d, time: %.2fs, cost: $%.4f, confidence: %.2f",
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
        
        # Primary model failed, try fallback models (1 attempt each)
        for fallback_model in fallback_models:
            logger.info(
                "Attempting fallback summary generation - model: %s, article: %s",
                fallback_model,
                article_title[:50] + "..."
            )
            
            try:
                start_time = time.time()
                
                # Get client
                client = self._get_client(fallback_model)
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", self._get_summary_system_prompt()),
                    ("human", self._get_summary_user_prompt(
                        article_title, article_content, article_url, source_name
                    )),
                ])
                
                formatted_prompt = prompt.format_messages()
                
                response = await self._ainvoke_json(client, formatted_prompt, fallback_model)
                
                # Log raw response for debugging
                logger.debug("RAW_RESP (model=%s): %s", fallback_model, response.content[:500] if hasattr(response, "content") else str(response)[:500])
                
                # Parse structured output with enhanced JSON extraction
                content = response.content.strip()
                
                # Try to extract JSON from various formats (same as primary model)
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
                
                # Method 3: Find JSON object in text (improved for multiline)
                if json_content is None:
                    # Look for complete JSON objects with summary_points, handling newlines
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
                    logger.debug("Fallback Method 6: Pure text to bullet conversion")
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
                        logger.debug("Fallback Method 6 successful: Created %d bullet points from text", 
                                   len(json_content["summary_points"]))
                
                # If we have JSON content, validate it with Pydantic
                if json_content:
                    try:
                        summary = SummaryOutput(**json_content)
                    except Exception as e:
                        logger.warning(f"Fallback Pydantic validation failed: {e}, using direct text parsing")
                        # Direct fallback to text parsing instead of problematic parser.parse()
                        summary = self._parse_text_to_summary(content)
                else:
                    # Direct text parsing instead of parser.parse() which causes KeyError
                    logger.debug("Fallback: No JSON found, parsing as text directly")
                    summary = self._parse_text_to_summary(content)
                
                # Validate summary
                self._validate_summary(summary)
                
                # Add metadata
                summary.model_used = fallback_model
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Estimate cost
                estimated_cost = self._estimate_cost(
                    fallback_model, self._get_summary_user_prompt(
                        article_title, article_content, article_url, source_name
                    ), response.content
                )
                
                logger.info(
                    "Fallback summary generation successful - model: %s, time: %.2fs, cost: $%.4f, confidence: %.2f",
                    fallback_model,
                    processing_time,
                    estimated_cost,
                    summary.confidence_score
                )
                
                return summary
                
            except Exception as e:
                last_error = e
                processing_time = time.time() - start_time
                
                logger.warning(
                    "Fallback summary generation failed - model: %s, error: %s, time: %.2fs",
                    fallback_model,
                    str(e),
                    processing_time
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
    
    def _get_summary_system_prompt(self) -> str:
        """Get system prompt for summary generation."""
        
        return """あなたは、日本のテクノロジー業界に精通した、高品質なAIニュースの専門編集者です。提供された記事から、読者にとって価値のある、詳細で情報豊富な日本語の要約を作成してください。

# 厳守すべき指示
- **出力形式**: 必ず指定されたJSON形式で、3〜4個の箇条書きポイントを生成してください。箇条書き以外のテキスト（挨拶、前置き、後書きなど）は一切含めないでください。
- **箇条書きの品質**: 各ポイントは、80文字以上120文字以内で（PRD厳守）、記事の核心（誰が、何をした、結果どうなった）を簡潔に記述してください。冗長な説明は避け、要点のみに集中してください。
- **文体**: 全ての文章は、です・ます調（敬体）で統一してください。
- **禁止事項**: 記事内容と無関係なメタコメントや、「この記事では〜」「〜と述べられています」のような定型的な指示語は絶対に使用しないでください。

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

# 具体的な高品質の出力例
{{
  "summary_points": [
    "OpenAI社がGPT-5を正式発表、前世代比で推論能力50%向上を達成しました。",
    "マルチモーダル機能を大幅強化、動画コンテンツの理解・生成が可能になりました。",
    "エンタープライズAPI提供は2025年Q3開始予定、企業開発に大きな影響が期待されます。",
    "医療・科学分野での活用を重点的に推進、研究機関との連携も強化する方針です。"
  ],
  "confidence_score": 0.95,
  "source_reliability": "high"
}}

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
            
            # Create a new, simpler prompt focused on summarizing the summary.
            prompt = f"""あなたはプロのニュース見出し編集者です。以下の記事要約から、読者の関心を引く魅力的で具体的な日本語見出しを生成してください。

# 記事要約
{chr(10).join(f'- {point}' for point in summary_points)}

# 見出し作成要件
## 基本要件
- **文字数**: 25-55文字（目安：30-45文字が最適）
- **形式**: 体言止めまたは動詞で締める
- **具体性**: 企業名・製品名・数値を必ず含める
- **魅力**: 読者が「詳細を知りたい」と思う内容

## 必須要素（優先順位順）
1. **具体的な企業名・製品名**（例：OpenAI、ChatGPT-4o、Gemini Pro）
2. **具体的な動作・結果**（例：50%向上、月内開始、3倍拡大）
3. **技術・分野の明示**（例：推論能力、画像認識、音声合成）
4. **市場・ユーザーへの影響**（例：企業向け、一般向け、開発者向け）

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
                
                # Remove quotes if present
                title = re.sub(r'^["\'「]|["\'」]$', '', title)
                # Remove any remaining newlines
                title = title.replace('\n', ' ').strip()
                
                # Enhanced validation with quality scoring
                if 10 <= len(title) <= 60:
                    # Quality scoring system
                    quality_score = 0
                    rejection_reasons = []
                    
                    # 1. Check for specific content (企業名・製品名)
                    companies = ['OpenAI', 'Google', 'Meta', 'Microsoft', 'Anthropic', 'Apple', 'Amazon', 'Tesla', 'NVIDIA']
                    products = ['ChatGPT', 'GPT-4', 'Gemini', 'Claude', 'Llama', 'Copilot', 'Bard']
                    
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
                    
                    # Final quality decision
                    min_quality_score = 3  # Require at least company/product + one other element
                    
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