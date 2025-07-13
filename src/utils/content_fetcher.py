"""
Content fetching utilities for RSS feeds and YouTube channels.

This module handles fetching and parsing content from various sources
including RSS feeds and YouTube RSS feeds.
"""

import asyncio
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

import aiohttp
import feedparser
import pytz
from aiohttp import BasicAuth
from bs4 import BeautifulSoup

from src.models.schemas import RawArticle, SourceConfig
from src.utils.logger import setup_logging

logger = setup_logging()


class ContentFetcher:
    """Handles fetching content from RSS and YouTube sources."""

    def __init__(self, timeout: int = 30, max_concurrent: int = 10):
        """
        Initialize the content fetcher.

        Args:
            timeout: Request timeout in seconds
            max_concurrent: Maximum concurrent requests
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_concurrent = max_concurrent
        self.session: aiohttp.ClientSession | None = None

        # User agent to avoid being blocked
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/91.0.4472.124 Safari/537.36 '
                'AI-Newsletter-Bot/1.0'
            )
        }

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers=self.headers
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def fetch_all_sources(
        self,
        sources: list[SourceConfig],
        max_items_per_source: int = 10,
        hours_lookback: int = 24
    ) -> list[RawArticle]:
        """
        Fetch articles from all enabled sources.

        Args:
            sources: List of source configurations
            max_items_per_source: Maximum articles per source
            hours_lookback: How many hours back to look for articles

        Returns:
            List of raw articles
        """

        enabled_sources = [s for s in sources if s.enabled]
        logger.info(
            "Starting content fetch",
            total_sources=len(sources),
            enabled_sources=len(enabled_sources),
            max_items_per_source=max_items_per_source,
            hours_lookback=hours_lookback
        )

        # Create semaphore for concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # Fetch from all sources concurrently
        tasks = []
        for source in enabled_sources:
            task = self._fetch_source_with_semaphore(
                semaphore, source, max_items_per_source, hours_lookback
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        all_articles = []
        successful_sources = 0

        for i, result in enumerate(results):
            source = enabled_sources[i]

            if isinstance(result, Exception):
                logger.error(
                    "Source fetch failed",
                    source_id=source.id,
                    error=str(result)
                )
            else:
                articles = result or []
                all_articles.extend(articles)
                successful_sources += 1

                logger.info(
                    "Source fetch completed",
                    source_id=source.id,
                    articles_count=len(articles)
                )

        logger.info(
            "Content fetch completed",
            successful_sources=successful_sources,
            total_articles=len(all_articles)
        )

        # Sort by publication date (newest first)
        all_articles.sort(key=lambda x: x.published_date, reverse=True)

        return all_articles

    async def _fetch_source_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        source: SourceConfig,
        max_items: int,
        hours_lookback: int
    ) -> list[RawArticle]:
        """Fetch from a single source with semaphore protection."""

        async with semaphore:
            try:
                if source.source_type == "rss":
                    return await self._fetch_rss_feed(source, max_items, hours_lookback)
                elif source.source_type == "youtube":
                    return await self._fetch_youtube_feed(source, max_items, hours_lookback)
                else:
                    logger.warning(
                        "Unknown source type",
                        source_id=source.id,
                        source_type=source.source_type
                    )
                    return []

            except Exception as e:
                logger.error(
                    "Source fetch exception",
                    source_id=source.id,
                    error=str(e),
                    exc_info=True
                )
                return []

    async def _fetch_rss_feed(
        self,
        source: SourceConfig,
        max_items: int,
        hours_lookback: int
    ) -> list[RawArticle]:
        """Fetch articles from RSS feed."""

        logger.debug("Fetching RSS feed", source_id=source.id, url=str(source.url))

        auth = None
        if source.authentication:
            if source.authentication.type == "basic":
                username = os.getenv(source.authentication.env_username)
                password = os.getenv(source.authentication.env_password)

                if username and password:
                    auth = BasicAuth(username, password)
                    logger.info(f"Using HTTP Basic Auth for {source.id}")
                else:
                    logger.warning(
                        f"Authentication configured for {source.id}, but credentials not in environment. "
                        f"Skipping source. Please set {source.authentication.env_username} and {source.authentication.env_password}."
                    )
                    return []

        try:
            async with self.session.get(str(source.url), auth=auth) as response:
                if response.status != 200:
                    logger.warning(
                        "RSS feed returned non-200 status",
                        source_id=source.id,
                        status=response.status
                    )
                    return []

                content = await response.text()

        except TimeoutError:
            logger.warning("RSS feed request timeout", source_id=source.id)
            return []
        except Exception as e:
            logger.error(
                "RSS feed request failed",
                source_id=source.id,
                error=str(e)
            )
            return []

        # Parse RSS content
        try:
            feed = feedparser.parse(content)

            if feed.bozo and feed.bozo_exception:
                logger.warning(
                    "RSS feed parsing issues",
                    source_id=source.id,
                    error=str(feed.bozo_exception)
                )

            articles = []
            cutoff_time = datetime.now(pytz.UTC) - timedelta(hours=hours_lookback)

            for entry in feed.entries[:max_items * 2]:  # Get extra in case some are filtered
                try:
                    article = self._parse_rss_entry(entry, source, cutoff_time)
                    if article:
                        articles.append(article)

                        if len(articles) >= max_items:
                            break

                except Exception as e:
                    logger.warning(
                        "RSS entry parsing failed",
                        source_id=source.id,
                        entry_title=getattr(entry, 'title', 'Unknown'),
                        error=str(e)
                    )
                    continue

            return articles

        except Exception as e:
            logger.error(
                "RSS feed parsing failed",
                source_id=source.id,
                error=str(e)
            )
            return []

    async def _fetch_youtube_feed(
        self,
        source: SourceConfig,
        max_items: int,
        hours_lookback: int
    ) -> list[RawArticle]:
        """Fetch videos from YouTube RSS feed."""

        logger.debug("Fetching YouTube feed", source_id=source.id, url=str(source.url))

        # YouTube RSS feeds are just RSS, so use the same logic
        return await self._fetch_rss_feed(source, max_items, hours_lookback)

    def _parse_rss_entry(
        self,
        entry: feedparser.FeedParserDict,
        source: SourceConfig,
        cutoff_time: datetime
    ) -> RawArticle | None:
        """Parse a single RSS entry into a RawArticle."""

        # Extract basic fields
        title = getattr(entry, 'title', '').strip()
        link = getattr(entry, 'link', '').strip()

        if not title or not link:
            return None

        # Parse publication date
        published_date = self._parse_date(entry)
        if published_date < cutoff_time:
            return None  # Too old

        # Extract content
        content = self._extract_content(entry)

        # Extract author
        author = getattr(entry, 'author', None)
        if not author and hasattr(entry, 'authors') and entry.authors:
            author = entry.authors[0].get('name', '') if entry.authors else None

        # Generate article ID
        article_id = self._generate_article_id(link, published_date)

        # Extract tags
        tags = list(source.tags)  # Start with source tags
        if hasattr(entry, 'tags') and entry.tags:
            tags.extend([tag.term for tag in entry.tags if hasattr(tag, 'term')])

        # Create article with priority setting
        article = RawArticle(
            id=article_id,
            title=title,
            url=link,
            published_date=published_date,
            content=content,
            source_id=source.id,
            source_type=source.source_type,
            author=author,
            tags=tags
        )

        # Set source priority based on source_id
        article.set_source_priority()

        return article

    def _parse_date(self, entry: feedparser.FeedParserDict) -> datetime:
        """Parse publication date from RSS entry."""

        # Try different date fields
        for field in ['published_parsed', 'updated_parsed']:
            if hasattr(entry, field):
                time_struct = getattr(entry, field)
                if time_struct:
                    try:
                        dt = datetime(*time_struct[:6])
                        return dt.replace(tzinfo=pytz.UTC)
                    except (ValueError, TypeError):
                        continue

        # Fallback to current time if no date found
        logger.warning(
            "No valid date found in RSS entry",
            entry_title=getattr(entry, 'title', 'Unknown')
        )
        return datetime.now(pytz.UTC)

    def _extract_content(self, entry: feedparser.FeedParserDict) -> str:
        """Extract content from RSS entry."""

        # Try different content fields in order of preference
        content_fields = [
            'content',
            'summary',
            'description',
            'subtitle'
        ]

        for field in content_fields:
            if hasattr(entry, field):
                content = getattr(entry, field)

                # Handle different content structures
                if isinstance(content, list) and content:
                    content = content[0]

                if isinstance(content, dict):
                    content = content.get('value', '')

                if isinstance(content, str) and content.strip():
                    # Clean HTML content
                    cleaned = self._clean_html_content(content)
                    if cleaned:
                        return cleaned

        return ""

    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content and extract text."""

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text and clean whitespace
            text = soup.get_text()
            text = re.sub(r'\s+', ' ', text).strip()

            # Limit length
            if len(text) > 2000:
                text = text[:2000] + "..."

            return text

        except Exception as e:
            logger.warning(
                "HTML content cleaning failed",
                error=str(e)
            )
            # Return cleaned version of original
            text = re.sub(r'<[^>]+>', '', html_content)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:2000] + "..." if len(text) > 2000 else text

    def _generate_article_id(self, url: str, published_date: datetime) -> str:
        """Generate unique article ID."""

        # Use domain + path + date for uniqueness
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        path = parsed.path.rstrip('/')
        date_str = published_date.strftime('%Y%m%d')

        # Create hash-like ID
        import hashlib
        content = f"{domain}{path}{date_str}"
        hash_obj = hashlib.md5(content.encode())

        return f"{domain}_{date_str}_{hash_obj.hexdigest()[:8]}"


async def fetch_content_from_sources(
    sources: list[SourceConfig],
    max_items_per_source: int = 10,
    hours_lookback: int = 24
) -> list[RawArticle]:
    """
    Convenience function to fetch content from all sources.

    Args:
        sources: List of source configurations
        max_items_per_source: Maximum articles per source
        hours_lookback: How many hours back to look

    Returns:
        List of raw articles
    """

    async with ContentFetcher() as fetcher:
        return await fetcher.fetch_all_sources(
            sources, max_items_per_source, hours_lookback
        )
