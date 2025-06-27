"""
Context analysis system for article relationships.

This module implements the contextual analysis that determines whether
articles are duplicates, updates, or independent content.
"""

import asyncio
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional

from src.llm.llm_router import LLMRouter
from src.models.schemas import ContextAnalysisResult, SummarizedArticle
from src.utils.embedding_manager import EmbeddingManager
from src.utils.logger import setup_logging

logger = setup_logging()


class ContextAnalyzer:
    """Analyzes contextual relationships between articles."""
    
    def __init__(
        self,
        embedding_manager: Optional[EmbeddingManager] = None,
        llm_router: Optional[LLMRouter] = None,
        prompts_dir: str = "src/prompts"
    ):
        """
        Initialize context analyzer.
        
        Args:
            embedding_manager: Embedding manager for similarity search
            llm_router: LLM router for context analysis
            prompts_dir: Directory containing prompt templates
        """
        self.embedding_manager = embedding_manager
        self.llm_router = llm_router or LLMRouter()
        self.prompts_dir = Path(prompts_dir)
        
        # Load prompts
        self.prompts = self._load_prompts()
    
    def _load_prompts(self) -> Dict:
        """Load context analysis prompts from YAML."""
        
        try:
            prompts_file = self.prompts_dir / "context_analysis.yaml"
            
            if not prompts_file.exists():
                logger.warning(f"Prompts file not found: {prompts_file}")
                return self._get_default_prompts()
            
            with open(prompts_file, 'r', encoding='utf-8') as f:
                prompts = yaml.safe_load(f)
            
            logger.debug("Loaded context analysis prompts")
            return prompts
            
        except Exception as e:
            logger.error("Failed to load prompts", error=str(e))
            return self._get_default_prompts()
    
    def _get_default_prompts(self) -> Dict:
        """Get default prompts if file loading fails."""
        
        return {
            "context_analysis_prompt": """
            今回のニュース: {current_title}
            過去の類似ニュース: {past_related_news}
            
            判定してください:
            - SKIP: 重複
            - UPDATE: 続報
            - KEEP: 独立記事
            
            JSON形式で回答:
            {{"decision": "SKIP|UPDATE|KEEP", "reasoning": "理由", "confidence_score": 0.85}}
            """,
            "system_prompt": "あなたはAIニュース記事の文脈分析専門家です。"
        }
    
    async def analyze_context(
        self,
        current_article: SummarizedArticle,
        max_similar_articles: int = 5,
        similarity_threshold: float = 0.7
    ) -> ContextAnalysisResult:
        """
        Analyze context of current article against past articles.
        
        Args:
            current_article: Article to analyze
            max_similar_articles: Maximum similar articles to consider
            similarity_threshold: Minimum similarity for comparison
        
        Returns:
            ContextAnalysisResult with decision and reasoning
        """
        
        try:
            article_id = current_article.filtered_article.raw_article.id
            article_title = current_article.filtered_article.raw_article.title
            
            logger.info(
                "Starting context analysis",
                article_id=article_id,
                article_title=article_title[:50] + "..." if len(article_title) > 50 else article_title,
                similarity_threshold=similarity_threshold,
                max_similar_articles=max_similar_articles
            )
            
            # Find similar past articles
            similar_articles = []
            
            if self.embedding_manager:
                similar_articles = await self.embedding_manager.search_similar_articles(
                    query_article=current_article,
                    top_k=max_similar_articles,
                    similarity_threshold=similarity_threshold
                )
                
                logger.info(
                    "Similar articles search completed",
                    article_id=article_id,
                    found_count=len(similar_articles),
                    similarity_scores=[round(a["similarity_score"], 3) for a in similar_articles[:3]]
                )
            else:
                logger.warning("Embedding manager not available for context analysis", article_id=article_id)
            
            if not similar_articles:
                # No similar articles found - treat as independent
                return ContextAnalysisResult(
                    decision="KEEP",
                    reasoning="過去に類似記事が見つからないため、独立した新しい記事として判定",
                    contextual_summary=None,
                    references=[],
                    similarity_score=0.0
                )
            
            # Analyze relationship using LLM
            analysis_result = await self._llm_context_analysis(
                current_article, similar_articles
            )
            
            logger.info(
                "Context analysis completed",
                article_id=current_article.filtered_article.raw_article.id,
                decision=analysis_result.decision,
                similar_articles_count=len(similar_articles),
                max_similarity=similar_articles[0]["similarity_score"] if similar_articles else 0
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error(
                "Context analysis failed",
                article_id=current_article.filtered_article.raw_article.id,
                error=str(e)
            )
            
            # Fallback to KEEP decision
            return ContextAnalysisResult(
                decision="KEEP",
                reasoning=f"文脈分析エラーのため独立記事として処理: {str(e)}",
                contextual_summary=None,
                references=[],
                similarity_score=0.0
            )
    
    async def _llm_context_analysis(
        self,
        current_article: SummarizedArticle,
        similar_articles: List[Dict]
    ) -> ContextAnalysisResult:
        """Use LLM to analyze article relationships."""
        
        try:
            raw_article = current_article.filtered_article.raw_article
            article_id = raw_article.id
            
            logger.info(
                "Starting LLM context analysis",
                article_id=article_id,
                similar_articles_count=len(similar_articles),
                max_similarity=similar_articles[0]["similarity_score"] if similar_articles else 0
            )
            
            # Prepare current article info
            current_info = {
                "title": raw_article.title,
                "content": raw_article.content[:1000],  # Limit for prompt
                "summary": " ".join(current_article.summary.summary_points),
                "date": raw_article.published_date.strftime("%Y-%m-%d")
            }
            
            # Prepare similar articles info
            past_news_text = ""
            reference_ids = []
            
            for i, article in enumerate(similar_articles):
                past_news_text += f"\n{i+1}. **{article['title']}**\n"
                past_news_text += f"   日付: {article['published_date'][:10]}\n"
                past_news_text += f"   類似度: {article['similarity_score']:.3f}\n"
                past_news_text += f"   要約: {article['content_summary'][:200]}...\n"
                
                reference_ids.append(article['article_id'])
            
            # Create analysis prompt
            prompt = self.prompts["context_analysis_prompt"].format(
                current_title=current_info["title"],
                current_content=current_info["content"],
                current_summary=current_info["summary"],
                current_date=current_info["date"],
                past_related_news=past_news_text
            )
            
            logger.debug(
                "Context analysis prompt prepared",
                article_id=article_id,
                prompt_length=len(prompt),
                similar_articles_in_prompt=len(similar_articles)
            )
            
            # Use LLM router for analysis
            system_prompt = self.prompts.get("system_prompt", "")
            
            # Create a temporary summary output structure for LLM router
            # We'll parse the JSON response manually
            try:
                response = await self._call_llm_for_context_analysis(
                    system_prompt, prompt
                )
                
                logger.info(
                    "LLM context analysis response received",
                    article_id=article_id,
                    response_length=len(response) if response else 0
                )
                
                # Parse LLM response
                analysis_data = self._parse_llm_response(response)
                
                # Create result with proper validation
                result = ContextAnalysisResult(
                    decision=analysis_data.get("decision", "KEEP"),
                    reasoning=analysis_data.get("reasoning", "LLM分析完了"),
                    contextual_summary=analysis_data.get("contextual_summary"),
                    references=reference_ids[:3],  # Limit references
                    similarity_score=similar_articles[0]["similarity_score"] if similar_articles else 0.0
                )
                
                logger.info(
                    "LLM context analysis completed",
                    article_id=article_id,
                    final_decision=result.decision,
                    reasoning_length=len(result.reasoning) if result.reasoning else 0,
                    has_contextual_summary=bool(result.contextual_summary),
                    references_count=len(result.references)
                )
                
                return result
                
            except Exception as llm_error:
                logger.error("LLM context analysis failed", error=str(llm_error))
                
                # Fallback decision based on similarity scores - 調整済み閾値でUPDATE検出を改善
                max_similarity = similar_articles[0]["similarity_score"] if similar_articles else 0.0
                
                if max_similarity > 0.85:
                    decision = "SKIP"
                    reasoning = f"高い類似度（{max_similarity:.3f}）により重複と判定"
                elif max_similarity > 0.65:  # 閾値を下げてUPDATE検出を改善
                    decision = "UPDATE"
                    reasoning = f"中程度の類似度（{max_similarity:.3f}）により続報と判定"
                else:
                    decision = "KEEP"
                    reasoning = f"類似度（{max_similarity:.3f}）により独立記事と判定"
                
                return ContextAnalysisResult(
                    decision=decision,
                    reasoning=reasoning,
                    contextual_summary=None,
                    references=reference_ids[:3],
                    similarity_score=max_similarity
                )
                
        except Exception as e:
            logger.error("LLM context analysis error", error=str(e))
            
            return ContextAnalysisResult(
                decision="KEEP",
                reasoning="分析エラーのため独立記事として処理",
                contextual_summary=None,
                references=[],
                similarity_score=0.0
            )
    
    async def _call_llm_for_context_analysis(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> str:
        """Call LLM for context analysis."""
        
        # Use a simpler approach for context analysis
        # since we need JSON response rather than structured summary
        from langchain_core.messages import HumanMessage, SystemMessage
        
        # Try each model in fallback order
        for model_name in self.llm_router.fallback_order:
            try:
                client = self.llm_router._get_client(model_name)
                
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                
                response = await client.ainvoke(messages)
                return response.content
                
            except Exception as e:
                logger.warning(f"Model {model_name} failed for context analysis", error=str(e))
                continue
        
        raise Exception("All LLM models failed for context analysis")
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM JSON response."""
        
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Find JSON in response (in case there's extra text)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                
                # Validate required fields
                if "decision" not in data:
                    data["decision"] = "KEEP"
                if "reasoning" not in data:
                    data["reasoning"] = "分析完了"
                if "confidence_score" not in data:
                    data["confidence_score"] = 0.5
                
                return data
            else:
                logger.warning("No JSON found in LLM response")
                return {"decision": "KEEP", "reasoning": "JSON解析失敗"}
                
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON response", error=str(e))
            return {"decision": "KEEP", "reasoning": "JSON解析エラー"}
        except Exception as e:
            logger.error("Unexpected error parsing LLM response", error=str(e))
            return {"decision": "KEEP", "reasoning": "解析エラー"}


async def analyze_article_context(
    article: SummarizedArticle,
    embedding_manager: Optional[EmbeddingManager] = None,
    llm_router: Optional[LLMRouter] = None
) -> ContextAnalysisResult:
    """
    Convenience function to analyze article context.
    
    Args:
        article: Article to analyze
        embedding_manager: Optional embedding manager
        llm_router: Optional LLM router
    
    Returns:
        ContextAnalysisResult
    """
    
    analyzer = ContextAnalyzer(embedding_manager, llm_router)
    return await analyzer.analyze_context(article)