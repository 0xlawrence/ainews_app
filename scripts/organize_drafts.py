#!/usr/bin/env python3
"""
Organize existing draft files into year/month subdirectories.
Usage: python scripts/organize_drafts.py
"""

import os
import shutil
import re
from datetime import datetime
from pathlib import Path

def organize_drafts(drafts_dir: str = "drafts"):
    """Organize existing draft files into YYYY/MM structure."""
    
    if not os.path.exists(drafts_dir):
        print(f"Error: {drafts_dir} directory not found")
        return
    
    # Pattern to match newsletter files: YYYY-MM-DD_HHMM_daily_newsletter.md
    pattern = re.compile(r'^(\d{4})-(\d{2})-(\d{2})_\d{4}_daily_newsletter\.md$')
    
    organized_count = 0
    skipped_count = 0
    
    for filename in os.listdir(drafts_dir):
        filepath = os.path.join(drafts_dir, filename)
        
        # Skip if it's a directory
        if os.path.isdir(filepath):
            continue
            
        # Check if filename matches our pattern
        match = pattern.match(filename)
        if not match:
            print(f"Skipping non-matching file: {filename}")
            skipped_count += 1
            continue
            
        year, month, day = match.groups()
        
        # Create target directory
        target_dir = os.path.join(drafts_dir, year, month)
        os.makedirs(target_dir, exist_ok=True)
        
        # Move file
        target_path = os.path.join(target_dir, filename)
        
        if os.path.exists(target_path):
            print(f"File already exists at target: {target_path}")
            continue
            
        try:
            shutil.move(filepath, target_path)
            print(f"Moved: {filename} -> {year}/{month}/")
            organized_count += 1
        except Exception as e:
            print(f"Error moving {filename}: {str(e)}")
    
    print(f"\nOrganization complete:")
    print(f"  Organized: {organized_count} files")
    print(f"  Skipped: {skipped_count} files")

def create_index_files(drafts_dir: str = "drafts"):
    """Create index.md files for each month with file listings."""
    
    for root, dirs, files in os.walk(drafts_dir):
        # Skip root directory
        if root == drafts_dir:
            continue
            
        # Only process month directories (should have format drafts/YYYY/MM)
        path_parts = Path(root).parts
        if len(path_parts) != 3:  # drafts, YYYY, MM
            continue
            
        year, month = path_parts[-2], path_parts[-1]
        
        # Filter newsletter files
        newsletter_files = [f for f in files if f.endswith('_daily_newsletter.md')]
        newsletter_files.sort(reverse=True)  # Most recent first
        
        if not newsletter_files:
            continue
            
        # Create index content
        index_content = f"# AI Newsletter Drafts - {year}/{month}\n\n"
        index_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        index_content += f"## Files ({len(newsletter_files)} total)\n\n"
        
        for filename in newsletter_files:
            # Extract date and time from filename
            match = re.match(r'^(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})_daily_newsletter\.md$', filename)
            if match:
                date, hour, minute = match.groups()
                index_content += f"- [{date} {hour}:{minute}]({filename})\n"
            else:
                index_content += f"- [{filename}]({filename})\n"
        
        # Write index file
        index_path = os.path.join(root, "index.md")
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        print(f"Created index: {index_path}")

def cleanup_empty_directories(drafts_dir: str = "drafts"):
    """Remove empty directories after organization."""
    
    for root, dirs, files in os.walk(drafts_dir, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if not os.listdir(dir_path):  # Directory is empty
                    os.rmdir(dir_path)
                    print(f"Removed empty directory: {dir_path}")
            except OSError:
                pass  # Directory not empty or other error

if __name__ == "__main__":
    print("🗂️  Organizing draft files...")
    
    # Step 1: Organize files into year/month structure
    organize_drafts()
    
    # Step 2: Create index files for each month
    print("\n📋 Creating index files...")
    create_index_files()
    
    # Step 3: Clean up empty directories
    print("\n🧹 Cleaning up empty directories...")
    cleanup_empty_directories()
    
    print("\n✅ Organization complete!")
    print("\nNew structure:")
    print("drafts/")
    print("├── 2025/")
    print("│   ├── 06/")
    print("│   │   ├── index.md")
    print("│   │   ├── 2025-06-22_1051_daily_newsletter.md")
    print("│   │   └── ...")
    print("│   └── 07/")
    print("└── ...") 