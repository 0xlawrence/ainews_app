"""
Advanced prompt management system for newsletter generation.

This module provides versioned prompt management, template rendering,
and prompt optimization capabilities for consistent LLM interactions.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, Template, TemplateError

from src.utils.logger import setup_logging

logger = setup_logging()


@dataclass
class PromptVersion:
    """Represents a versioned prompt."""
    version: str
    content: str
    metadata: dict[str, Any]
    created_at: datetime
    hash_id: str

    @classmethod
    def from_content(cls, content: str, version: str = "1.0", metadata: dict = None):
        """Create prompt version from content."""
        metadata = metadata or {}
        hash_id = hashlib.md5(content.encode()).hexdigest()[:8]

        return cls(
            version=version,
            content=content,
            metadata=metadata,
            created_at=datetime.now(),
            hash_id=hash_id
        )


@dataclass
class PromptTemplate:
    """Represents a prompt template with variables."""
    name: str
    description: str
    template_content: str
    variables: list[str]
    default_values: dict[str, Any]
    tags: list[str]
    versions: dict[str, PromptVersion]

    def render(self, variables: dict[str, Any] = None, version: str = "latest") -> str:
        """Render template with provided variables."""
        variables = variables or {}

        # Get the specified version
        if version == "latest":
            version_key = max(self.versions.keys()) if self.versions else "1.0"
        else:
            version_key = version

        if version_key not in self.versions:
            raise ValueError(f"Version {version_key} not found for template {self.name}")

        prompt_version = self.versions[version_key]

        # Merge with default values
        render_vars = {**self.default_values, **variables}

        try:
            template = Template(prompt_version.content)
            return template.render(**render_vars)
        except TemplateError as e:
            logger.error(f"Template rendering failed for {self.name}: {e}")
            raise


class PromptManager:
    """Advanced prompt management system."""

    def __init__(self, prompts_dir: str = "src/prompts"):
        """Initialize prompt manager."""
        self.prompts_dir = Path(prompts_dir)
        self.templates: dict[str, PromptTemplate] = {}
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Metrics
        self.usage_stats: dict[str, int] = {}
        self.performance_stats: dict[str, list[float]] = {}

        # Load existing prompts
        self._load_prompts()

    def _load_prompts(self):
        """Load all prompts from the prompts directory."""
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory {self.prompts_dir} does not exist")
            return

        # Load YAML prompt files
        for yaml_file in self.prompts_dir.glob("*.yaml"):
            try:
                self._load_yaml_prompts(yaml_file)
            except Exception as e:
                logger.error(f"Failed to load prompts from {yaml_file}: {e}")

        # Load JSON prompt files
        for json_file in self.prompts_dir.glob("*.json"):
            try:
                self._load_json_prompts(json_file)
            except Exception as e:
                logger.error(f"Failed to load prompts from {json_file}: {e}")

        logger.info(f"Loaded {len(self.templates)} prompt templates")

    def _load_yaml_prompts(self, yaml_file: Path):
        """Load prompts from a YAML file."""
        with open(yaml_file, encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            logger.warning(f"Invalid YAML structure in {yaml_file}")
            return

        for prompt_name, prompt_data in data.items():
            if isinstance(prompt_data, str):
                # Simple string prompt
                template = PromptTemplate(
                    name=prompt_name,
                    description=f"Prompt from {yaml_file.name}",
                    template_content=prompt_data,
                    variables=self._extract_variables(prompt_data),
                    default_values={},
                    tags=[yaml_file.stem],
                    versions={"1.0": PromptVersion.from_content(prompt_data)}
                )
            elif isinstance(prompt_data, dict):
                # Structured prompt definition
                template = PromptTemplate(
                    name=prompt_name,
                    description=prompt_data.get('description', ''),
                    template_content=prompt_data.get('template', prompt_data.get('content', '')),
                    variables=prompt_data.get('variables', []),
                    default_values=prompt_data.get('defaults', {}),
                    tags=prompt_data.get('tags', [yaml_file.stem]),
                    versions={}
                )

                # Handle versioned content
                if 'versions' in prompt_data:
                    for version, content in prompt_data['versions'].items():
                        template.versions[version] = PromptVersion.from_content(
                            content, version, prompt_data.get('metadata', {})
                        )
                else:
                    # Single version
                    template.versions["1.0"] = PromptVersion.from_content(
                        template.template_content, "1.0", prompt_data.get('metadata', {})
                    )

            self.templates[prompt_name] = template

    def _load_json_prompts(self, json_file: Path):
        """Load prompts from a JSON file."""
        with open(json_file, encoding='utf-8') as f:
            data = json.load(f)

        if 'prompts' in data:
            prompts_data = data['prompts']
        else:
            prompts_data = data

        for prompt_name, prompt_config in prompts_data.items():
            template = PromptTemplate(
                name=prompt_name,
                description=prompt_config.get('description', ''),
                template_content=prompt_config.get('template', ''),
                variables=prompt_config.get('variables', []),
                default_values=prompt_config.get('defaults', {}),
                tags=prompt_config.get('tags', [json_file.stem]),
                versions={}
            )

            # Load versions
            if 'versions' in prompt_config:
                for version, content in prompt_config['versions'].items():
                    template.versions[version] = PromptVersion.from_content(
                        content, version
                    )
            else:
                template.versions["1.0"] = PromptVersion.from_content(
                    template.template_content
                )

            self.templates[prompt_name] = template

    def _extract_variables(self, template_content: str) -> list[str]:
        """Extract Jinja2 variables from template content."""
        import re

        # Find {{ variable }} patterns
        pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
        variables = re.findall(pattern, template_content)

        return list(set(variables))

    def get_prompt(
        self,
        name: str,
        variables: dict[str, Any] = None,
        version: str = "latest"
    ) -> str:
        """Get rendered prompt by name."""
        if name not in self.templates:
            raise KeyError(f"Prompt template '{name}' not found")

        template = self.templates[name]

        # Track usage
        self.usage_stats[name] = self.usage_stats.get(name, 0) + 1

        # Render and return
        start_time = datetime.now()
        try:
            result = template.render(variables, version)

            # Track performance
            duration = (datetime.now() - start_time).total_seconds()
            if name not in self.performance_stats:
                self.performance_stats[name] = []
            self.performance_stats[name].append(duration)

            return result

        except Exception as e:
            logger.error(f"Failed to render prompt {name}: {e}")
            raise

    def list_prompts(self) -> list[dict[str, Any]]:
        """List all available prompt templates."""
        prompts = []

        for name, template in self.templates.items():
            prompts.append({
                "name": name,
                "description": template.description,
                "variables": template.variables,
                "tags": template.tags,
                "versions": list(template.versions.keys()),
                "usage_count": self.usage_stats.get(name, 0)
            })

        return prompts

    def search_prompts(
        self,
        query: str = None,
        tags: list[str] = None,
        variables: list[str] = None
    ) -> list[str]:
        """Search prompts by criteria."""
        matching_prompts = []

        for name, template in self.templates.items():
            match = True

            # Query match (name or description)
            if query:
                if query.lower() not in name.lower() and query.lower() not in template.description.lower():
                    match = False

            # Tags match
            if tags:
                if not any(tag in template.tags for tag in tags):
                    match = False

            # Variables match
            if variables:
                if not any(var in template.variables for var in variables):
                    match = False

            if match:
                matching_prompts.append(name)

        return matching_prompts

    def add_prompt(
        self,
        name: str,
        content: str,
        description: str = "",
        variables: list[str] = None,
        defaults: dict[str, Any] = None,
        tags: list[str] = None,
        version: str = "1.0"
    ) -> PromptTemplate:
        """Add a new prompt template."""
        variables = variables or self._extract_variables(content)
        defaults = defaults or {}
        tags = tags or ["user_defined"]

        template = PromptTemplate(
            name=name,
            description=description,
            template_content=content,
            variables=variables,
            default_values=defaults,
            tags=tags,
            versions={version: PromptVersion.from_content(content, version)}
        )

        self.templates[name] = template
        logger.info(f"Added prompt template: {name}")

        return template

    def update_prompt(
        self,
        name: str,
        content: str = None,
        description: str = None,
        version: str = None
    ) -> PromptTemplate:
        """Update an existing prompt template."""
        if name not in self.templates:
            raise KeyError(f"Prompt template '{name}' not found")

        template = self.templates[name]

        if description is not None:
            template.description = description

        if content is not None:
            if version is None:
                # Auto-increment version
                existing_versions = [float(v) for v in template.versions.keys() if v.replace('.', '').isdigit()]
                if existing_versions:
                    next_version = str(max(existing_versions) + 0.1)
                else:
                    next_version = "1.1"
            else:
                next_version = version

            template.versions[next_version] = PromptVersion.from_content(content, next_version)
            template.template_content = content
            template.variables = self._extract_variables(content)

        logger.info(f"Updated prompt template: {name}")
        return template

    def save_prompts(self, output_file: str = None):
        """Save all prompt templates to file."""
        if output_file is None:
            output_file = self.prompts_dir / "managed_prompts.json"

        output_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_prompts": len(self.templates),
                "usage_stats": self.usage_stats
            },
            "prompts": {}
        }

        for name, template in self.templates.items():
            output_data["prompts"][name] = {
                "description": template.description,
                "variables": template.variables,
                "defaults": template.default_values,
                "tags": template.tags,
                "versions": {
                    version: {
                        "content": pv.content,
                        "metadata": pv.metadata,
                        "created_at": pv.created_at.isoformat(),
                        "hash_id": pv.hash_id
                    }
                    for version, pv in template.versions.items()
                }
            }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(self.templates)} prompts to {output_file}")

    def get_performance_report(self) -> dict[str, Any]:
        """Get performance report for prompt usage."""
        report = {
            "total_prompts": len(self.templates),
            "total_usage": sum(self.usage_stats.values()),
            "most_used_prompts": sorted(
                self.usage_stats.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "performance_stats": {}
        }

        for prompt_name, durations in self.performance_stats.items():
            if durations:
                import statistics
                report["performance_stats"][prompt_name] = {
                    "calls": len(durations),
                    "avg_duration": statistics.mean(durations),
                    "max_duration": max(durations),
                    "min_duration": min(durations)
                }

        return report


# Enhanced prompt templates for Phase 3
ENHANCED_PROMPTS = {
    "summary_with_validation": {
        "description": "Enhanced summary generation with quality validation",
        "template": """
あなたは AI ニュース記事の専門要約者です。以下の記事を正確で簡潔な日本語で要約してください。

## 要約ルール
1. 必ず3-4個の箇条書きで要約する
2. 各項目は50-200文字以内
3. 指示語（この、その、あの、どの）は使用禁止
4. 各項目は「です」「ます」「した」「きます」で終える
5. 具体的な数値や固有名詞を必ず含める

## 記事情報
**タイトル**: {{ article_title }}
**URL**: {{ article_url }}
**ソース**: {{ source_name }}
**内容**: {{ article_content }}

## 要約（3-4項目の箇条書き）:
""",
        "variables": ["article_title", "article_url", "source_name", "article_content"],
        "defaults": {
            "source_name": "不明"
        },
        "tags": ["summary", "validation", "phase3"]
    },

    "quality_check": {
        "description": "Content quality validation prompt",
        "template": """
以下の要約の品質を評価してください。

## 評価基準
1. 文字数: 各項目50-200文字
2. 指示語禁止: 「この」「その」「あの」「どの」を含まない
3. 適切な語尾: 「です」「ます」「した」「きます」で終わる
4. 項目数: 3-4項目
5. 具体性: 具体的な情報を含む

## 要約内容
{% for point in summary_points %}
{{ loop.index }}. {{ point }}
{% endfor %}

## 評価結果 (JSON形式で回答):
{
  "is_valid": boolean,
  "quality_score": float (0.0-1.0),
  "violations": [
    {
      "rule": "違反ルール名",
      "message": "詳細メッセージ",
      "severity": "error/warning"
    }
  ],
  "suggestions": ["改善提案1", "改善提案2"]
}
""",
        "variables": ["summary_points"],
        "tags": ["quality", "validation", "phase3"]
    }
}


def get_default_prompt_manager() -> PromptManager:
    """Get default prompt manager with enhanced prompts."""
    manager = PromptManager()

    # Add enhanced prompts for Phase 3
    for name, config in ENHANCED_PROMPTS.items():
        manager.add_prompt(
            name=name,
            content=config["template"],
            description=config["description"],
            variables=config["variables"],
            defaults=config.get("defaults", {}),
            tags=config["tags"]
        )

    return manager
