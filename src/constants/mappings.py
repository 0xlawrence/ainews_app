"""
Centralized mappings for company names, products, and sources.

This module provides consistent mappings used across the application
for formatting company names, product names, and source identifiers.
"""

# Company name mappings (for consistent display)
COMPANY_MAPPINGS = {
    "openai": "OpenAI",
    "chatgpt": "ChatGPT", 
    "gpt": "GPT",
    "google": "Google",
    "alphabet": "Alphabet",
    "deepmind": "DeepMind",
    "gemini": "Gemini",
    "bard": "Bard",
    "meta": "Meta",
    "facebook": "Facebook",
    "instagram": "Instagram",
    "microsoft": "Microsoft",
    "azure": "Azure",
    "copilot": "Copilot",
    "apple": "Apple",
    "iphone": "iPhone",
    "ipad": "iPad",
    "macos": "macOS",
    "amazon": "Amazon",
    "aws": "AWS",
    "alexa": "Alexa",
    "nvidia": "NVIDIA",
    "tesla": "Tesla",
    "spacex": "SpaceX",
    "anthropic": "Anthropic",
    "claude": "Claude",
    "ibm": "IBM",
    "watson": "Watson",
    "samsung": "Samsung",
    "lg": "LG",
    "sony": "Sony"
}

# Product/Technology name mappings
PRODUCT_MAPPINGS = {
    "gpt": "GPT",
    "chatgpt": "ChatGPT",
    "claude": "Claude",
    "gemini": "Gemini",
    "llama": "LLaMA",
    "dall-e": "DALL-E",
    "dall·e": "DALL-E",
    "midjourney": "Midjourney",
    "stable diffusion": "Stable Diffusion",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "hugging face": "Hugging Face",
    "transformers": "Transformers"
}

# Source name mappings for citation formatting
SOURCE_MAPPINGS = {
    "techcrunch": "TechCrunch",
    "theverge": "The Verge", 
    "the_verge": "The Verge",
    "wired": "WIRED",
    "openai_blog": "OpenAI Blog",
    "openai_news": "OpenAI Official",
    "anthropic_news": "Anthropic Official",
    "google_ai_blog": "Google AI Blog",
    "google_research": "Google Research",
    "youtube_tech": "AI Tech Channel",
    "arxiv": "arXiv",
    "github": "GitHub",
    "huggingface": "Hugging Face",
    "nature": "Nature",
    "science": "Science Magazine",
    "venturebeat": "VentureBeat",
    "venturebeat_ai": "VentureBeat AI"
}

# Enhanced source mappings with credibility indicators
CREDIBLE_SOURCE_MAPPINGS = {
    "techcrunch": "TechCrunch",
    "the_verge": "The Verge", 
    "wired": "WIRED",
    "openai_news": "OpenAI Official",
    "google_research": "Google Research",
    "anthropic_news": "Anthropic Official",
    "nature": "Nature",
    "science": "Science Magazine",
    "arxiv": "arXiv",
    "huggingface": "Hugging Face"
}

# Regex patterns for company detection
COMPANY_PATTERNS = [
    r'(OpenAI|ChatGPT|GPT-\d+)',
    r'(Google|Alphabet|DeepMind|Gemini)',
    r'(Meta|Facebook|Instagram)',
    r'(Microsoft|Azure|Copilot)',
    r'(Apple|iPhone|iPad|macOS)',
    r'(Amazon|AWS|Alexa)',
    r'(NVIDIA|Tesla|SpaceX)',
    r'(Anthropic|Claude)',
    r'(IBM|Watson)',
    r'(Samsung|LG|Sony)'
]

# Regex patterns for product detection
PRODUCT_PATTERNS = [
    r'(GPT-\d+(?:\.\d+)?|ChatGPT|GPT)',
    r'(Claude(?:-\d+)?)',
    r'(Gemini(?:\s+\d+\.\d+)?)',
    r'(LLaMA|Llama)',
    r'(DALL-E|DALL·E)',
    r'(Midjourney)',
    r'(Stable\s+Diffusion)',
    r'(PyTorch|TensorFlow)',
    r'(Transformers)',
    r'(Hugging\s+Face)'
]

# Tech keyword classifications
TECH_KEYWORDS = {
    'ai', 'artificial', 'intelligence', 'machine', 'learning', 'neural',
    'deep', 'model', 'gpt', 'llm', 'openai', 'google', 'meta', 'anthropic',
    'transformer', 'embedding', 'training', 'inference', 'pytorch', 'tensorflow'
}

# Reputable news domains for source bonus calculation
REPUTABLE_DOMAINS = {
    'techcrunch.com', 'theverge.com', 'wired.com', 'venturebeat.com',
    'arstechnica.com', 'engadget.com', 'zdnet.com', 'cnet.com'
}

# Official company domains
OFFICIAL_DOMAINS = {
    'openai.com', 'google.com', 'meta.com', 'anthropic.com',
    'microsoft.com', 'apple.com', 'amazon.com', 'nvidia.com'
}


def format_company_name(name: str) -> str:
    """Format a company name using the standardized mappings."""
    return COMPANY_MAPPINGS.get(name.lower(), name.title())


def format_product_name(name: str) -> str:
    """Format a product name using the standardized mappings."""
    return PRODUCT_MAPPINGS.get(name.lower(), name)


def format_source_name(source_id: str) -> str:
    """Format a source ID into a proper display name."""
    return SOURCE_MAPPINGS.get(source_id.lower(), source_id.replace('_', ' ').title())


def is_reputable_domain(domain: str) -> bool:
    """Check if a domain is considered reputable for news."""
    return domain.lower() in REPUTABLE_DOMAINS


def is_official_domain(domain: str) -> bool:
    """Check if a domain is an official company domain."""
    return any(official in domain.lower() for official in OFFICIAL_DOMAINS)