"""
Output management and file saving for newsletters.

This module handles file saving, content validation, directory management,
and output path generation for newsletter creation.
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from src.models.schemas import ProcessedArticle, NewsletterOutput
    from src.config.settings import get_settings
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False

logger = logging.getLogger(__name__)


class OutputManager:
    """Handles newsletter output management and file operations."""
    
    def __init__(self, default_output_dir: str = "drafts"):
        """Initialize output manager.
        
        Args:
            default_output_dir: Default directory for saving newsletters
        """
        self.default_output_dir = default_output_dir
        if HAS_DEPENDENCIES:
            self.settings = get_settings()
        else:
            self.settings = None
        
        logger.info("Output Manager initialized")
    
    def save_newsletter(
        self,
        content: str,
        date: datetime,
        edition: str = "daily",
        output_dir: Optional[str] = None
    ) -> Path:
        """Save newsletter content to file with timestamp and edition.
        
        Args:
            content: Newsletter content to save
            date: Date of the newsletter
            edition: Newsletter edition type
            output_dir: Output directory (uses default if None)
            
        Returns:
            Path to the saved file
        """
        output_dir = output_dir or self.default_output_dir
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename – include HHMM to avoid overwrite and aid manual comparison
        # "2025-06-22_0135_daily_newsletter.md" のような形式になる
        date_str = date.strftime("%Y-%m-%d_%H%M")
        filename = f"{date_str}_{edition}_newsletter.md"

        output_file = output_path / filename

        # Write content
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Newsletter saved: {output_file}")

        except Exception as e:
            logger.error(f"Failed to save newsletter: file={output_file}, error={str(e)}")
            raise

        return output_file

    def save_to_file_organized(self, content: str, output_dir: Optional[str] = None) -> str:
        """Save newsletter content to markdown file with organized directory structure.
        
        Args:
            content: Newsletter content to save
            output_dir: Base output directory (uses default if None)
            
        Returns:
            Path to the saved file as string
        """
        output_dir = output_dir or self.default_output_dir
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")

        # Create organized directory structure: drafts/YYYY/MM/
        year = datetime.now().strftime("%Y")
        month = datetime.now().strftime("%m")
        organized_dir = os.path.join(output_dir, year, month)

        # Ensure directory exists
        os.makedirs(organized_dir, exist_ok=True)

        filename = f"{timestamp}_daily_newsletter.md"
        filepath = os.path.join(organized_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Newsletter saved to: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to save newsletter: {str(e)}")
            # Fallback to flat structure if organized save fails
            fallback_path = os.path.join(output_dir, filename)
            with open(fallback_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Newsletter saved to fallback location: {fallback_path}")
            return fallback_path

    def validate_and_fix_newsletter_content(
        self,
        content: str,
        articles: List['ProcessedArticle']
    ) -> str:
        """
        Validate and fix newsletter content for quality issues.

        Args:
            content: Generated newsletter content
            articles: Source articles for validation

        Returns:
            Fixed newsletter content
        """

        if not content:
            return ""

        # Fix common formatting issues
        content = re.sub(r'\n{3,}', '\n\n', content)  # Limit consecutive newlines
        content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)  # Remove trailing whitespace
        content = content.strip()

        # Ensure proper line endings
        if not content.endswith('\n'):
            content += '\n'

        # Validate that all articles are represented
        missing_articles = []
        for article in articles:
            if hasattr(article, 'japanese_title') and article.japanese_title:
                # Check if article title appears in content
                if article.japanese_title not in content:
                    missing_articles.append(article)

        if missing_articles:
            logger.warning(f"Found {len(missing_articles)} articles missing from newsletter content")

        return content

    def generate_filename(
        self,
        date: datetime,
        edition: str = "daily",
        include_time: bool = True,
        extension: str = ".md"
    ) -> str:
        """Generate filename for newsletter.
        
        Args:
            date: Date of the newsletter
            edition: Newsletter edition type
            include_time: Whether to include time in filename
            extension: File extension
            
        Returns:
            Generated filename
        """
        if include_time:
            date_str = date.strftime("%Y-%m-%d_%H%M")
        else:
            date_str = date.strftime("%Y-%m-%d")
        
        return f"{date_str}_{edition}_newsletter{extension}"

    def create_organized_directory(
        self,
        base_dir: str,
        date: Optional[datetime] = None,
        structure: str = "year_month"
    ) -> Path:
        """Create organized directory structure.
        
        Args:
            base_dir: Base directory path
            date: Date for directory structure (uses current if None)
            structure: Directory structure type ("year_month", "year", "flat")
            
        Returns:
            Path to the created directory
        """
        if date is None:
            date = datetime.now()
        
        base_path = Path(base_dir)
        
        if structure == "year_month":
            year = date.strftime("%Y")
            month = date.strftime("%m")
            organized_path = base_path / year / month
        elif structure == "year":
            year = date.strftime("%Y")
            organized_path = base_path / year
        else:  # flat
            organized_path = base_path
        
        # Create directory if it doesn't exist
        organized_path.mkdir(parents=True, exist_ok=True)
        
        return organized_path

    def backup_existing_file(self, filepath: Path) -> Optional[Path]:
        """Create backup of existing file if it exists.
        
        Args:
            filepath: Path to the file to backup
            
        Returns:
            Path to backup file if created, None otherwise
        """
        if not filepath.exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = filepath.with_stem(f"{filepath.stem}_backup_{timestamp}")
        
        try:
            import shutil
            shutil.copy2(filepath, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
            return None

    def save_newsletter_with_metadata(
        self,
        content: str,
        metadata: Dict[str, Any],
        output_dir: Optional[str] = None,
        create_backup: bool = False
    ) -> Dict[str, Any]:
        """Save newsletter with metadata and optional backup.
        
        Args:
            content: Newsletter content
            metadata: Newsletter metadata (date, edition, articles_count, etc.)
            output_dir: Output directory
            create_backup: Whether to create backup if file exists
            
        Returns:
            Dictionary with save results and file paths
        """
        output_dir = output_dir or self.default_output_dir
        
        # Extract metadata
        date = metadata.get('date', datetime.now())
        edition = metadata.get('edition', 'daily')
        
        # Generate filepath
        organized_dir = self.create_organized_directory(output_dir, date)
        filename = self.generate_filename(date, edition)
        filepath = organized_dir / filename
        
        result = {
            'success': False,
            'filepath': str(filepath),
            'backup_path': None,
            'error': None
        }
        
        try:
            # Create backup if requested and file exists
            if create_backup:
                backup_path = self.backup_existing_file(filepath)
                result['backup_path'] = str(backup_path) if backup_path else None
            
            # Validate and fix content
            validated_content = self.validate_and_fix_newsletter_content(
                content, 
                metadata.get('articles', [])
            )
            
            # Save newsletter
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(validated_content)
            
            # Save metadata file alongside newsletter
            metadata_filepath = filepath.with_suffix('.json')
            self._save_metadata(metadata, metadata_filepath)
            
            result['success'] = True
            result['metadata_path'] = str(metadata_filepath)
            logger.info(f"Newsletter saved successfully: {filepath}")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Failed to save newsletter: {e}")
        
        return result

    def _save_metadata(self, metadata: Dict[str, Any], filepath: Path) -> None:
        """Save metadata to JSON file.
        
        Args:
            metadata: Metadata dictionary
            filepath: Path to save metadata file
        """
        try:
            import json
            
            # Create serializable metadata
            serializable_metadata = {}
            for key, value in metadata.items():
                if key == 'date' and isinstance(value, datetime):
                    serializable_metadata[key] = value.isoformat()
                elif key == 'articles':
                    # Save article count and titles only for metadata
                    serializable_metadata['articles_count'] = len(value) if value else 0
                    serializable_metadata['article_titles'] = [
                        getattr(article, 'japanese_title', 'Unknown Title') 
                        for article in (value or [])
                    ]
                else:
                    try:
                        # Test if value is JSON serializable
                        json.dumps(value)
                        serializable_metadata[key] = value
                    except (TypeError, ValueError):
                        # Convert non-serializable values to string
                        serializable_metadata[key] = str(value)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(serializable_metadata, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Metadata saved: {filepath}")
            
        except Exception as e:
            logger.warning(f"Failed to save metadata: {e}")

    def cleanup_old_files(
        self,
        output_dir: Optional[str] = None,
        days_to_keep: int = 30,
        pattern: str = "*_newsletter.md"
    ) -> Dict[str, Any]:
        """Clean up old newsletter files.
        
        Args:
            output_dir: Directory to clean (uses default if None)
            days_to_keep: Number of days to keep files
            pattern: File pattern to match for cleanup
            
        Returns:
            Dictionary with cleanup results
        """
        output_dir = output_dir or self.default_output_dir
        
        result = {
            'files_deleted': 0,
            'space_freed': 0,
            'errors': []
        }
        
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            output_path = Path(output_dir)
            
            if not output_path.exists():
                return result
            
            # Find files matching pattern
            for file_path in output_path.rglob(pattern):
                try:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime < cutoff_date:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        
                        result['files_deleted'] += 1
                        result['space_freed'] += file_size
                        
                        logger.debug(f"Deleted old file: {file_path}")
                        
                except Exception as e:
                    error_msg = f"Failed to delete {file_path}: {e}"
                    result['errors'].append(error_msg)
                    logger.warning(error_msg)
            
            if result['files_deleted'] > 0:
                logger.info(
                    f"Cleanup completed: {result['files_deleted']} files deleted, "
                    f"{result['space_freed']} bytes freed"
                )
            
        except Exception as e:
            result['errors'].append(f"Cleanup failed: {e}")
            logger.error(f"Cleanup failed: {e}")
        
        return result

    def get_recent_files(
        self,
        output_dir: Optional[str] = None,
        limit: int = 10,
        pattern: str = "*_newsletter.md"
    ) -> List[Dict[str, Any]]:
        """Get list of recent newsletter files.
        
        Args:
            output_dir: Directory to search (uses default if None)
            limit: Maximum number of files to return
            pattern: File pattern to match
            
        Returns:
            List of dictionaries with file information
        """
        output_dir = output_dir or self.default_output_dir
        output_path = Path(output_dir)
        
        if not output_path.exists():
            return []
        
        files = []
        
        try:
            # Find and sort files by modification time
            file_paths = list(output_path.rglob(pattern))
            file_paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            for file_path in file_paths[:limit]:
                stat = file_path.stat()
                files.append({
                    'path': str(file_path),
                    'name': file_path.name,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'relative_path': str(file_path.relative_to(output_path))
                })
                
        except Exception as e:
            logger.warning(f"Failed to get recent files: {e}")
        
        return files

    def validate_output_directory(self, output_dir: str) -> Dict[str, Any]:
        """Validate output directory and permissions.
        
        Args:
            output_dir: Directory path to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': False,
            'exists': False,
            'writable': False,
            'readable': False,
            'errors': []
        }
        
        try:
            path = Path(output_dir)
            
            # Check if path exists
            result['exists'] = path.exists()
            
            if not result['exists']:
                # Try to create directory
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    result['exists'] = True
                except Exception as e:
                    result['errors'].append(f"Cannot create directory: {e}")
                    return result
            
            # Check if it's a directory
            if not path.is_dir():
                result['errors'].append("Path exists but is not a directory")
                return result
            
            # Check permissions
            result['readable'] = os.access(path, os.R_OK)
            result['writable'] = os.access(path, os.W_OK)
            
            if not result['readable']:
                result['errors'].append("Directory is not readable")
            
            if not result['writable']:
                result['errors'].append("Directory is not writable")
            
            result['valid'] = result['exists'] and result['readable'] and result['writable']
            
        except Exception as e:
            result['errors'].append(f"Validation failed: {e}")
        
        return result