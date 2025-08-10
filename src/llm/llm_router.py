"""
Refactored LLM Router with modular architecture.

This module provides a clean, modular LLM routing system using
separate components for client management, response parsing,
retry handling, and prompt templating.
"""

import asyncio
import logging
import time
from typing import Union, List, Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate

from src.config.settings import get_settings
from src.models.schemas import ProcessedArticle, SummaryOutput
from src.utils.text_processing import clean_llm_response

# Lazy import pattern: import inside methods to avoid heavy deps at import time
from .client_factory import LLMClientFactory
from .response_parser import ResponseParser, CostEstimator
from .retry_handler import RetryHandler
from .prompt_templates import PromptTemplates

logger = logging.getLogger(__name__)


class LLMRouter:
    """Refactored LLM router with modular architecture."""

    def __init__(self):
        """Initialize the modular LLM router."""
        self.settings = get_settings()
        
        # Initialize modular components
        self.client_factory = LLMClientFactory()
        self.response_parser = ResponseParser()
        self.cost_estimator = CostEstimator()
        self.retry_handler = RetryHandler(
            self.client_factory, 
            self.response_parser, 
            self.cost_estimator
        )
        self.prompt_templates = PromptTemplates()
        
        logger.info("Modular LLM Router initialized successfully")

    async def generate_summary(
        self,
        article_title: str,
        article_content: str,
        article_url: str,
        source_name: str,
        max_retries: Union[int, None] = None
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

        # Prepare prompts using template system
        system_prompt = self.prompt_templates.get_summary_system_prompt()
        user_prompt = self.prompt_templates.get_summary_user_prompt(
            article_title, article_content, article_url, source_name
        )

        # Execute with retry and fallback logic
        async def summary_operation(model_name: str, **kwargs) -> SummaryOutput:
            return await self._generate_summary_with_model(
                model_name, system_prompt, user_prompt, **kwargs
            )

        operation_args = {
            "article_title": article_title,
            "article_content": article_content,
            "article_url": article_url,
            "source_name": source_name
        }

        result = await self.retry_handler.execute_with_fallback(
            summary_operation,
            operation_args,
            max_retries=max_retries,
            operation_name="summary_generation"
        )

        return result

    async def _generate_summary_with_model(
        self,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> SummaryOutput:
        """Generate summary with a specific model."""
        start_time = time.time()

        # Get client
        client = self.client_factory.get_client(model_name)

        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt),
        ])

        formatted_prompt = prompt.format_messages()
        
        # Make API call
        response = await self.retry_handler.ainvoke_with_retry(client, formatted_prompt, model_name)

        # Parse response
        summary = self.response_parser.extract_summary_from_response(response.content, model_name)
        if not summary:
            raise ValueError("Failed to extract valid summary from response")

        # Validate summary
        self.response_parser.validate_summary(summary)

        # Add metadata
        summary.model_used = model_name
        summary.processing_time_seconds = time.time() - start_time
        summary.total_tokens = len(user_prompt + response.content) // 4  # Rough estimate

        return summary

    async def generate_simple_text(
        self,
        prompt: str,
        max_tokens: int = 200,
        temperature: float = 0.3,
        max_retries: int = 2
    ) -> Union[str, None]:
        """
        Generate simple text using LLM with retry logic.

        Args:
            prompt: Text prompt for generation
            max_tokens: Maximum tokens in response
            temperature: Temperature for generation
            max_retries: Maximum retry attempts

        Returns:
            Generated text or None if all attempts fail
        """
        async def text_operation(model_name: str, **kwargs) -> str:
            return await self._generate_simple_text_with_model(
                model_name, prompt, max_tokens, temperature
            )

        operation_args = {"prompt": prompt}

        try:
            result = await self.retry_handler.execute_with_fallback(
                text_operation,
                operation_args,
                max_retries=max_retries,
                operation_name="simple_text_generation"
            )
            return result
        except Exception as e:
            logger.error(f"Simple text generation failed: {e}")
            return None

    async def _generate_simple_text_with_model(
        self,
        model_name: str,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> str:
        """Generate simple text with a specific model."""
        client = self.client_factory.get_client(model_name)

        # Create simple prompt
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompt_templates.get_simple_text_system_prompt()),
            ("human", prompt),
        ])

        formatted_prompt = chat_prompt.format_messages()
        response = await self.retry_handler.ainvoke_with_retry(client, formatted_prompt, model_name)

        if not response or not response.content:
            raise ValueError("Empty response from LLM")

        # Clean response
        cleaned_response = clean_llm_response(response.content.strip())
        return cleaned_response

    async def generate_citation_based_summary(
        self,
        article_title: str,
        article_content: str,
        article_url: str,
        source_name: str,
        citations: List[Dict[str, str]],
        max_retries: int = 2
    ) -> SummaryOutput:
        """
        Generate citation-based summary (PRD F-15 compliance).

        Args:
            article_title: Title of the main article
            article_content: Content of the main article
            article_url: URL of the main article
            source_name: Name of the source
            citations: List of citation dictionaries
            max_retries: Maximum retry attempts

        Returns:
            Enhanced SummaryOutput with citation integration
        """
        # Prepare prompts
        system_prompt = self.prompt_templates.get_citation_based_system_prompt()
        user_prompt = self.prompt_templates.get_citation_based_user_prompt(
            article_title, article_content, article_url, source_name, citations
        )

        async def citation_operation(model_name: str, **kwargs) -> SummaryOutput:
            return await self._generate_summary_with_model(
                model_name, system_prompt, user_prompt, **kwargs
            )

        operation_args = {
            "article_title": article_title,
            "article_content": article_content,
            "article_url": article_url,
            "source_name": source_name,
            "citations": citations
        }

        result = await self.retry_handler.execute_with_fallback(
            citation_operation,
            operation_args,
            max_retries=max_retries,
            operation_name="citation_based_summary"
        )

        return result

    async def generate_japanese_title(
        self,
        article: ProcessedArticle,
        max_tokens: int = 100,
        temperature: float = 0.3
    ) -> Union[str, None]:
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

            if not summary_points:
                return None

            # Check if this is an UPDATE article
            is_update = getattr(article, 'is_update', False)

            # Generate title prompt
            prompt = self.prompt_templates.get_title_generation_prompt(summary_points, is_update)

            # Generate title
            result = await self.generate_simple_text(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                max_retries=2
            )

            if result:
                # Clean title and remove conversation artifacts
                cleaned_title = self._clean_title_artifacts(result)
                
                # Add update emoji if needed
                if is_update and not cleaned_title.startswith('🆙'):
                    cleaned_title = f"🆙 {cleaned_title}"
                
                return cleaned_title

            return None

        except Exception as e:
            logger.error(f"Japanese title generation failed: {e}")
            return None

    def _clean_title_artifacts(self, title: str) -> str:
        """Clean conversation artifacts from generated titles."""
        import re
        
        # Remove conversation artifacts
        conversation_artifacts = [
            r'^はい、?承知[いし]?ました。?.*',
            r'^プロの?ニュース見出し編集者として.*',
            r'^記事要約から.*見出しを.*[生作成]成.*',
            r'^以下に?、?.*見出し.*提案.*',
            r'^魅力的で?具体的な?日本語見出し.*',
            r'^.*以下のような見出し.*',
            r'^.*記事の見出し.*',
            r'^.*見出しを.*生成.*'
        ]
        
        for pattern in conversation_artifacts:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE | re.MULTILINE)
        
        # Clean up whitespace and common formatting
        title = title.strip()
        title = re.sub(r'^[「『"""]|[」』"""]$', '', title)  # Remove quotes
        title = re.sub(r'^\s*[-•]\s*', '', title)  # Remove bullet points
        title = re.sub(r'^\d+\.\s*', '', title)  # Remove numbering
        
        return title.strip()

    # Batch Processing Methods (Phase 3.2c optimization)

    async def generate_summaries_batch(
        self,
        articles: List[Dict[str, Any]],
        batch_size: Optional[int] = None,
        max_concurrent_batches: Optional[int] = None
    ) -> List[Optional[SummaryOutput]]:
        """
        Generate summaries for multiple articles using batch processing.
        
        This method significantly improves performance by:
        - Processing articles in batches to reduce API call overhead
        - Using concurrent batch processing to maximize throughput
        - Maintaining input order in results
        - Providing graceful fallback for failed items
        
        Args:
            articles: List of article dictionaries with title, content, url, source_name
            batch_size: Number of articles per batch (uses config default if None)
            max_concurrent_batches: Maximum concurrent batches (uses config default if None)
            
        Returns:
            List of SummaryOutput objects in same order as input (None for failed items)
        """
        if not articles:
            return []
            
        # Use configuration defaults if not specified
        settings = get_settings()
        effective_batch_size = batch_size or settings.processing.llm_batch_size
        effective_max_batches = max_concurrent_batches or settings.processing.max_concurrent_llm_batches
        
        if not settings.processing.enable_llm_batch_processing:
            # Fall back to individual processing
            logger.info("LLM batch processing disabled, using individual processing")
            return await self._process_articles_individually(articles)
        
        logger.info(f"Processing {len(articles)} articles in batches of {effective_batch_size}")
        
        # Step 1: Create batches
        batches = []
        batch_indices = []
        
        for i in range(0, len(articles), effective_batch_size):
            batch_articles = articles[i:i + effective_batch_size]
            batch_idx = list(range(i, min(i + effective_batch_size, len(articles))))
            batches.append(batch_articles)
            batch_indices.append(batch_idx)
        
        # Step 2: Process batches concurrently with semaphore
        semaphore = asyncio.Semaphore(effective_max_batches)
        results = [None] * len(articles)
        
        async def process_batch(batch_articles: List[Dict], batch_idx: List[int]) -> List[tuple]:
            """Process a single batch of articles."""
            async with semaphore:
                batch_results = []
                
                try:
                    # Create batch prompt that processes multiple articles at once
                    batch_prompt = self._create_batch_summary_prompt(batch_articles)
                    
                    # Generate batch response
                    batch_response = await self.generate_simple_text(
                        prompt=batch_prompt,
                        max_tokens=200 * len(batch_articles),  # Scale tokens with batch size
                        temperature=0.3,
                        max_retries=2
                    )
                    
                    if batch_response:
                        logger.info(f"Batch response received: {batch_response[:1000]}...")
                        
                        # Parse batch response into individual summaries
                        individual_summaries = self._parse_batch_summary_response(
                            batch_response, batch_articles
                        )
                        
                        for j, (article, summary_text) in enumerate(zip(batch_articles, individual_summaries)):
                            if summary_text:
                                try:
                                    # Convert text to SummaryOutput
                                    summary = self._convert_text_to_summary_output(
                                        summary_text, article, "batch_processed"
                                    )
                                    # Attach batch processing metadata for downstream compatibility
                                    setattr(summary, "processing_time_seconds", 0.5)
                                    setattr(summary, "retry_count", 0)
                                    setattr(summary, "fallback_used", False)
                                    batch_results.append((batch_idx[j], summary))
                                except Exception as e:
                                    logger.error(f"Failed to convert batch summary {j}: {e}")
                                    batch_results.append((batch_idx[j], None))
                            else:
                                batch_results.append((batch_idx[j], None))
                    else:
                        # If batch processing fails, fall back to individual processing
                        logger.warning(f"Batch processing failed for {len(batch_articles)} articles, using individual fallback")
                        individual_results = await self._process_batch_individually(batch_articles)
                        
                        for j, result in enumerate(individual_results):
                            batch_results.append((batch_idx[j], result))
                    
                    logger.debug(f"Batch processed {len(batch_results)} articles")
                    return batch_results
                
                except Exception as e:
                    logger.error(f"Batch processing exception: {e}")
                    # Return None for all items in failed batch
                    return [(idx, None) for idx in batch_idx]
        
        # Step 3: Execute all batches concurrently
        batch_tasks = [
            process_batch(batch_articles, batch_idx)
            for batch_articles, batch_idx in zip(batches, batch_indices)
        ]
        
        start_time = time.time()
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        processing_time = time.time() - start_time
        
        # Step 4: Merge batch results back into original order
        successful_batches = 0
        total_summaries_generated = 0
        
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.error(f"Batch processing exception: {batch_result}")
                continue
                
            successful_batches += 1
            for original_idx, summary in batch_result:
                results[original_idx] = summary
                if summary is not None:
                    total_summaries_generated += 1
        
        # Step 5: Log performance metrics
        success_rate = (total_summaries_generated / len(articles)) * 100 if articles else 100
        
        logger.info(
            f"Batch summary generation completed: "
            f"{total_summaries_generated}/{len(articles)} generated, "
            f"{success_rate:.1f}% success rate, "
            f"{processing_time:.2f}s total, "
            f"{len(batches)} batches processed"
        )
        
        return results

    async def generate_titles_batch(
        self,
        articles: List[ProcessedArticle],
        batch_size: Optional[int] = None,
        max_concurrent_batches: Optional[int] = None
    ) -> List[Optional[str]]:
        """
        Generate Japanese titles for multiple articles using batch processing.
        
        Args:
            articles: List of ProcessedArticle objects
            batch_size: Number of articles per batch (uses config default if None)
            max_concurrent_batches: Maximum concurrent batches (uses config default if None)
            
        Returns:
            List of Japanese titles in same order as input (None for failed items)
        """
        if not articles:
            return []
            
        settings = get_settings()
        effective_batch_size = batch_size or settings.processing.llm_batch_size
        effective_max_batches = max_concurrent_batches or settings.processing.max_concurrent_llm_batches
        
        if not settings.processing.enable_llm_batch_processing:
            # Fall back to individual processing
            logger.info("LLM batch processing disabled for titles, using individual processing")
            return await self._process_titles_individually(articles)
        
        logger.info(f"Processing {len(articles)} titles in batches of {effective_batch_size}")
        
        # Create batches
        batches = []
        batch_indices = []
        
        for i in range(0, len(articles), effective_batch_size):
            batch_articles = articles[i:i + effective_batch_size]
            batch_idx = list(range(i, min(i + effective_batch_size, len(articles))))
            batches.append(batch_articles)
            batch_indices.append(batch_idx)
        
        # Process batches concurrently
        semaphore = asyncio.Semaphore(effective_max_batches)
        results = [None] * len(articles)
        
        async def process_title_batch(batch_articles: List[ProcessedArticle], batch_idx: List[int]) -> List[tuple]:
            """Process a single batch of title generation."""
            async with semaphore:
                try:
                    # Create batch title prompt
                    batch_prompt = self._create_batch_title_prompt(batch_articles)
                    
                    # Generate batch response
                    batch_response = await self.generate_simple_text(
                        prompt=batch_prompt,
                        max_tokens=100 * len(batch_articles),
                        temperature=0.3,
                        max_retries=2
                    )
                    
                    if batch_response:
                        # Parse batch response into individual titles
                        individual_titles = self._parse_batch_title_response(
                            batch_response, batch_articles
                        )
                        
                        batch_results = []
                        for j, (article, title) in enumerate(zip(batch_articles, individual_titles)):
                            if title:
                                try:
                                    # Apply title cleaning and update handling
                                    cleaned_title = self._clean_title_artifacts(title)
                                    
                                    # Add update emoji if needed
                                    is_update = getattr(article, 'is_update', False)
                                    if is_update and not cleaned_title.startswith('🆙'):
                                        cleaned_title = f"🆙 {cleaned_title}"
                                    
                                    batch_results.append((batch_idx[j], cleaned_title))
                                except Exception as e:
                                    logger.error(f"Failed to process batch title {j}: {e}")
                                    batch_results.append((batch_idx[j], None))
                            else:
                                batch_results.append((batch_idx[j], None))
                        
                        return batch_results
                    else:
                        # Fall back to individual processing
                        individual_results = await self._process_title_batch_individually(batch_articles)
                        return [(batch_idx[j], result) for j, result in enumerate(individual_results)]
                
                except Exception as e:
                    logger.error(f"Title batch processing exception: {e}")
                    return [(idx, None) for idx in batch_idx]
        
        # Execute batches
        batch_tasks = [
            process_title_batch(batch_articles, batch_idx)
            for batch_articles, batch_idx in zip(batches, batch_indices)
        ]
        
        start_time = time.time()
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        processing_time = time.time() - start_time
        
        # Merge results
        successful_titles = 0
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.error(f"Title batch processing exception: {batch_result}")
                continue
                
            for original_idx, title in batch_result:
                results[original_idx] = title
                if title is not None:
                    successful_titles += 1
        
        success_rate = (successful_titles / len(articles)) * 100 if articles else 100
        
        logger.info(
            f"Batch title generation completed: "
            f"{successful_titles}/{len(articles)} generated, "
            f"{success_rate:.1f}% success rate, "
            f"{processing_time:.2f}s total"
        )
        
        return results

    # Batch Processing Helper Methods

    def _create_batch_summary_prompt(self, articles: List[Dict[str, Any]]) -> str:
        """Create a batch prompt for summarizing multiple articles."""
        batch_prompt = """以下の複数記事について、それぞれ4つの箇条書きで日本語要約を生成してください。

重要：必ず以下の形式で出力してください：

記事1:
- 箇条書き1
- 箇条書き2  
- 箇条書き3
- 箇条書き4

記事2:
- 箇条書き1
- 箇条書き2
- 箇条書き3
- 箇条書き4

記事3:
- 箇条書き1
- 箇条書き2
- 箇条書き3
- 箇条書き4

（以下同様）

各記事は===で区切られています。

記事内容:
"""
        
        for i, article in enumerate(articles, 1):
            batch_prompt += f"\n=== 記事{i} ===\n"
            batch_prompt += f"タイトル: {article['title']}\n"
            batch_prompt += f"内容: {article['content'][:2000]}...\n"  # Limit content length
        
        return batch_prompt

    def _create_batch_title_prompt(self, articles: List[ProcessedArticle]) -> str:
        """Create a batch prompt for generating multiple article titles."""
        batch_prompt = """以下の記事要約から、それぞれ魅力的な日本語見出しを生成してください。各記事は===で区切られています。

要件:
- 各見出しは50文字以内
- 具体的で興味を引く内容
- 記事番号を含めて出力

出力形式：
記事1: [生成された見出し]
記事2: [生成された見出し]
...

記事要約:
"""
        
        for i, article in enumerate(articles, 1):
            batch_prompt += f"\n=== 記事{i} ===\n"
            try:
                summary_points = article.summarized_article.summary.summary_points
                batch_prompt += f"要約: {' / '.join(summary_points[:3])}\n"
            except (AttributeError, IndexError):
                batch_prompt += "要約: 記事要約が利用できません\n"
        
        return batch_prompt

    def _parse_batch_summary_response(self, response: str, articles: List[Dict]) -> List[Optional[str]]:
        """Parse batch summary response into individual summaries."""
        try:
            logger.debug(f"Parsing batch response for {len(articles)} articles")
            logger.debug(f"Response preview: {response[:500]}...")

            import re

            # Prefer robust capture: get content per article using non-greedy lookahead to next marker
            block_pattern = re.compile(r"記事(\d+):\s*(.*?)(?=記事\d+:|$)", re.DOTALL)
            blocks = {int(m.group(1)): m.group(2).strip() for m in block_pattern.finditer(response)}

            results: List[Optional[str]] = []
            for i in range(1, len(articles) + 1):
                section = blocks.get(i, "").strip()
                if not section:
                    logger.warning(f"Article {i} no section found via robust capture")
                    results.append(None)
                    continue

                bullet_points: List[str] = []

                # 1) Multi-line bullets: lines starting with -, •, *
                for line in section.split('\n'):
                    line = line.strip()
                    if line.startswith('- ') or line.startswith('• ') or line.startswith('* '):
                        point = line[2:].strip()
                        if 20 <= len(point) <= 500:
                            bullet_points.append(point)

                # 2) Regex capture bullets within a single line: - xxx - yyy - zzz
                if len(bullet_points) < 2:
                    inline_matches = re.findall(r'-\s+([^\-\n][^\n]*?)(?=\s+-\s+|$)', section)
                    for point in inline_matches:
                        p = point.strip()
                        if 20 <= len(p) <= 500:
                            bullet_points.append(p)

                # 3) Last resort: split by ' - ' separator
                if len(bullet_points) < 2 and ' - ' in section:
                    parts = re.split(r'\s*-\s*', section)
                    for part in parts:
                        p = part.strip()
                        if p and not p.lower().startswith(f'記事{i}:') and 20 <= len(p) <= 500:
                            bullet_points.append(p)

                logger.debug(f"Article {i} found {len(bullet_points)} bullet points")

                if len(bullet_points) >= 2:
                    results.append('\n'.join(bullet_points[:4]))
                else:
                    logger.warning(f"Article {i} insufficient bullet points: {len(bullet_points)}")
                    results.append(None)

            logger.debug(
                f"Parsing results: {len([r for r in results if r is not None])}/{len(results)} successful"
            )
            return results

        except Exception as e:
            logger.error(f"Failed to parse batch summary response: {e}")
            return [None] * len(articles)

    def _parse_batch_title_response(self, response: str, articles: List[ProcessedArticle]) -> List[Optional[str]]:
        """Parse batch title response into individual titles."""
        try:
            import re
            
            # Extract titles using pattern matching
            pattern = r'記事(\d+):\s*(.+?)(?=記事\d+:|$)'
            matches = re.findall(pattern, response, re.DOTALL)
            
            results = [None] * len(articles)
            
            for match in matches:
                try:
                    article_num = int(match[0]) - 1  # Convert to 0-based index
                    title = match[1].strip()
                    
                    if 0 <= article_num < len(articles) and 10 <= len(title) <= 100:
                        results[article_num] = title
                except (ValueError, IndexError):
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to parse batch title response: {e}")
            return [None] * len(articles)

    def _convert_text_to_summary_output(self, summary_text: str, article: Dict, model_name: str) -> SummaryOutput:
        """Convert summary text to SummaryOutput object."""
        # Split into bullet points
        lines = summary_text.split('\n')
        summary_points = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('• '):
                point = line[2:].strip()
                if point:
                    summary_points.append(point)
        
        if not summary_points:
            # Fallback: use the entire text as one point
            summary_points = [summary_text.strip()]
        
        return SummaryOutput(
            summary_points=summary_points[:4],  # Limit to 4 points
            confidence_score=0.8,  # Default confidence for batch processing
            source_reliability="medium",
            model_used=model_name,
            fallback_used=False,
            total_tokens=len(summary_text) // 4,  # Rough estimate
            processing_time_seconds=0.5  # Estimated per-article time in batch
        )

    async def _process_articles_individually(self, articles: List[Dict]) -> List[Optional[SummaryOutput]]:
        """Fallback method to process articles individually."""
        results = []
        
        for article in articles:
            try:
                summary = await self.generate_summary(
                    article_title=article['title'],
                    article_content=article['content'],
                    article_url=article['url'],
                    source_name=article['source_name']
                )
                results.append(summary)
            except Exception as e:
                logger.error(f"Individual article processing failed: {e}")
                results.append(None)
        
        return results

    async def _process_titles_individually(self, articles: List[ProcessedArticle]) -> List[Optional[str]]:
        """Fallback method to process titles individually."""
        results = []
        
        for article in articles:
            try:
                title = await self.generate_japanese_title(article)
                results.append(title)
            except Exception as e:
                logger.error(f"Individual title processing failed: {e}")
                results.append(None)
        
        return results

    async def _process_batch_individually(self, articles: List[Dict]) -> List[Optional[SummaryOutput]]:
        """Process a failed batch individually as fallback."""
        return await self._process_articles_individually(articles)

    async def _process_title_batch_individually(self, articles: List[ProcessedArticle]) -> List[Optional[str]]:
        """Process a failed title batch individually as fallback."""
        return await self._process_titles_individually(articles)

    # Utility methods

    def get_client_stats(self) -> Dict[str, Any]:
        """Get statistics about cached clients."""
        return {
            "cached_clients": list(self.client_factory.get_cached_clients().keys()),
            "retry_stats": self.retry_handler.get_retry_stats(),
            "supported_cost_models": self.cost_estimator.get_supported_models(),
            "available_templates": self.prompt_templates.get_available_templates()
        }

    def clear_caches(self):
        """Clear all internal caches."""
        self.client_factory.clear_cache()
        logger.info("All LLM Router caches cleared")

    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all LLM providers."""
        health_status = {}
        
        for model_name in ["gemini", "claude", "openai"]:
            try:
                client = self.client_factory.get_client(model_name)
                # Simple test prompt
                result = await self.generate_simple_text(
                    "テスト", max_tokens=10, max_retries=1
                )
                health_status[model_name] = result is not None
            except Exception as e:
                logger.warning(f"Health check failed for {model_name}: {e}")
                health_status[model_name] = False
        
        return health_status