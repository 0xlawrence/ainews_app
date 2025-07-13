"""
ソース優先順位の設定

優先順位:
1. 公式リリース系 (priority: 1) - 最上位
2. ニュースレター系 (priority: 2) - 次点
3. メディア・YouTube系 (priority: 3) - 同列
4. 日本語系ソース (priority: 4) - 最下位
"""

from enum import IntEnum


class SourcePriority(IntEnum):
    """ソース優先順位の定義"""
    OFFICIAL_RELEASES = 1    # 公式リリース系（最上位）
    NEWSLETTERS = 2          # ニュースレター系（次点）
    MEDIA_YOUTUBE = 3        # メディア・YouTube系（同列）
    JAPANESE_SOURCES = 4     # 日本語系ソース（最下位）

# 各ソースIDの優先順位マッピング
SOURCE_PRIORITY_MAP: dict[str, int] = {
    # 1. 公式リリース系 (priority: 1) - 最上位
    "openai_news": SourcePriority.OFFICIAL_RELEASES,
    "openai_research": SourcePriority.OFFICIAL_RELEASES,
    "anthropic_news": SourcePriority.OFFICIAL_RELEASES,
    "google_research_blog": SourcePriority.OFFICIAL_RELEASES,
    "google_gemini_blog": SourcePriority.OFFICIAL_RELEASES,
    "huggingface_blog": SourcePriority.OFFICIAL_RELEASES,
    "huggingface_daily_papers": SourcePriority.OFFICIAL_RELEASES,
    "anthropic_youtube": SourcePriority.OFFICIAL_RELEASES,
    "openai_youtube": SourcePriority.OFFICIAL_RELEASES,
    "googledeepmind_youtube": SourcePriority.OFFICIAL_RELEASES,

    # 2. ニュースレター系 (priority: 2) - 次点
    "nextword_ai": SourcePriority.NEWSLETTERS,
    "bay_area_times": SourcePriority.NEWSLETTERS,
    "ai_newsletter_saravia": SourcePriority.NEWSLETTERS,
    "semianalysis": SourcePriority.NEWSLETTERS,
    "tldr_ai": SourcePriority.NEWSLETTERS,
    "stratechery": SourcePriority.NEWSLETTERS,
    "import_ai": SourcePriority.NEWSLETTERS,
    "startup_archive": SourcePriority.NEWSLETTERS,
    "digital_native": SourcePriority.NEWSLETTERS,
    "recode_china_ai": SourcePriority.NEWSLETTERS,

    # 3. メディア・YouTube系 (priority: 3) - 同列
    "techcrunch": SourcePriority.MEDIA_YOUTUBE,
    "ieee_spectrum_ai": SourcePriority.MEDIA_YOUTUBE,
    "venturebeat_ai": SourcePriority.MEDIA_YOUTUBE,
    "wired_ai": SourcePriority.MEDIA_YOUTUBE,
    "the_decoder": SourcePriority.MEDIA_YOUTUBE,
    "the_information": SourcePriority.MEDIA_YOUTUBE,
    "hacker_news_ai": SourcePriority.MEDIA_YOUTUBE,
    "smol_ai_news": SourcePriority.MEDIA_YOUTUBE,
    "htdocs_dev": SourcePriority.MEDIA_YOUTUBE,
    "ycombinator_youtube": SourcePriority.MEDIA_YOUTUBE,
    "lexfridman_youtube": SourcePriority.MEDIA_YOUTUBE,
    "a16z_youtube": SourcePriority.MEDIA_YOUTUBE,
    "sequoia_youtube": SourcePriority.MEDIA_YOUTUBE,
    "lennys_podcast_youtube": SourcePriority.MEDIA_YOUTUBE,

    # 4. 日本語系ソース (priority: 4) - 最下位
    "zenn_llm": SourcePriority.JAPANESE_SOURCES,
    "zenn_ai_general": SourcePriority.JAPANESE_SOURCES,
    "note_ai_japan": SourcePriority.JAPANESE_SOURCES,
    "qiita_ai": SourcePriority.JAPANESE_SOURCES,
}

# カテゴリ別ソースリスト（可読性向上用）
PRIORITY_CATEGORIES: dict[str, list[str]] = {
    "公式リリース系": [
        "openai_news", "openai_research", "anthropic_news",
        "google_research_blog", "google_gemini_blog",
        "huggingface_blog", "huggingface_daily_papers",
        "anthropic_youtube", "openai_youtube", "googledeepmind_youtube"
    ],
    "ニュースレター系": [
        "nextword_ai", "bay_area_times", "ai_newsletter_saravia",
        "semianalysis", "tldr_ai", "stratechery", "import_ai",
        "startup_archive", "digital_native", "recode_china_ai"
    ],
    "メディア・YouTube系": [
        "techcrunch", "ieee_spectrum_ai", "venturebeat_ai",
        "wired_ai", "the_decoder", "the_information",
        "hacker_news_ai", "smol_ai_news", "htdocs_dev",
        "ycombinator_youtube", "lexfridman_youtube",
        "a16z_youtube", "sequoia_youtube", "lennys_podcast_youtube"
    ],
    "日本語系ソース": [
        "zenn_llm", "zenn_ai_general", "note_ai_japan", "qiita_ai"
    ]
}


def get_source_priority(source_id: str) -> int:
    """
    ソースIDから優先順位を取得

    Args:
        source_id: ソースID

    Returns:
        優先順位 (1=最高, 4=最低)、未定義の場合は3（メディア）
    """
    return SOURCE_PRIORITY_MAP.get(source_id, SourcePriority.MEDIA_YOUTUBE)


def get_priority_description(priority: int) -> str:
    """
    優先順位の説明を取得

    Args:
        priority: 優先順位番号

    Returns:
        優先順位の説明文
    """
    descriptions = {
        SourcePriority.OFFICIAL_RELEASES: "公式リリース系（最上位）",
        SourcePriority.NEWSLETTERS: "ニュースレター系（次点）",
        SourcePriority.MEDIA_YOUTUBE: "メディア・YouTube系（同列）",
        SourcePriority.JAPANESE_SOURCES: "日本語系ソース（最下位）"
    }
    return descriptions.get(priority, "未分類")


def sort_sources_by_priority(source_ids: list[str]) -> list[str]:
    """
    ソースIDのリストを優先順位でソート

    Args:
        source_ids: ソースIDのリスト

    Returns:
        優先順位順にソートされたソースIDリスト
    """
    return sorted(source_ids, key=get_source_priority)


def get_sources_by_priority(priority: int) -> list[str]:
    """
    特定の優先順位のソースIDリストを取得

    Args:
        priority: 取得したい優先順位

    Returns:
        該当する優先順位のソースIDリスト
    """
    return [source_id for source_id, p in SOURCE_PRIORITY_MAP.items() if p == priority]
