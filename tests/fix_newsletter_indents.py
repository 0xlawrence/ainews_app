#!/usr/bin/env python3
"""Fix indentation errors in newsletter_generator.py"""

import re

with open('src/utils/newsletter_generator.py', 'r') as f:
    content = f.read()

# List of precise fixes to apply
fixes = [
    # Fix import statements after try:
    (r'(try:\n)from (src\.models\.schemas)', r'\1    from \2'),
    (r'(try:\n    from src\.utils\.logger import setup_logging\n)logger = setup_logging\(\)', r'\1    logger = setup_logging()'),
    
    # Fix self.jinja_env block
    (r'(        if HAS_JINJA2 and jinja2:\n)        (self\.jinja_env = jinja2\.Environment)', r'\1            \2'),
    
    # Fix logger.info blocks after if HAS_LOGGER:
    (r'(        if HAS_LOGGER:\n)        (logger\.info\()', r'\1            \2'),
    
    # Fix template_name line
    (r'(        if self\.jinja_env:\n            # Use Jinja2 template rendering\n)        (template_name =)', r'\1            \2'),
    
    # Fix try block for template
    (r'(\n)        (try:\n            template = self\.jinja_env\.get_template)', r'\1            \2'),
    
    # Fix logger.warning in except block
    (r'(            except Exception:.*\n)            (logger\.warning\()', r'\1                \2'),
    
    # Fix nested try for daily_newsletter.jinja2
    (r'(                \)\n)                (try:\n)            (template = self\.jinja_env\.get_template\("daily_newsletter)', 
     r'\1\2                    \3'),
    
    # Fix if template: try: block
    (r'(        if template:\n)        (try:\n)            (newsletter_content = template\.render)', 
     r'\1            \2                \3'),
    
    # Fix except block
    (r'(                newsletter_content = template\.render.*\n)        (except Exception as e:)', r'\1            \2'),
    
    # Fix logger.error blocks
    (r'(                if HAS_LOGGER:\n)            (logger\.error\()', r'\1                    \2'),
    
    # Fix raise statement
    (r'(                    \)\n)            (raise)', r'\1                \2'),
]

# Apply all fixes
for pattern, replacement in fixes:
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

# Write back
with open('src/utils/newsletter_generator.py', 'w') as f:
    f.write(content)

print("Applied indentation fixes") 