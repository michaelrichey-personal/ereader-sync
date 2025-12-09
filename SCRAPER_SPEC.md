# Scraper Specification

This document describes how to create custom scrapers that integrate with the e-reader system's GUI and TUI.

## Overview

Scrapers are Python scripts that fetch content from web sources and convert them to EPUB format. They must follow a standard interface to work with the GUI/TUI automation.

## Directory Structure

All scrapers must be placed in:
```
bin/scrapers/
```

## Required Structure

###1. File Naming

Scraper files should follow the naming pattern:
```
scrape_<source>_to_epub.py
```

Examples:
- `scrape_hn_to_epub.py` - Hacker News scraper
- `scrape_hcr_to_epub.py` - Heather Cox Richardson scraper
- `scrape_reddit_to_epub.py` - Custom Reddit scraper (example)

### 2. Shebang and Executable

All scrapers must:
- Start with `#!/usr/bin/env python3`
- Be executable: `chmod +x bin/scrapers/scrape_*.py`

### 3. Required Imports

```python
#!/usr/bin/env python3
"""
Brief description of what this scraper does.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.common import suppress_urllib3_warning, output_progress
from config_reader import get_config, get_repo_root

# Suppress urllib3 warning
suppress_urllib3_warning()
```

### 4. Configuration

Scrapers should read configuration from `config/application.config` using the `get_config()` function:

```python
config = get_config()
repo_root = get_repo_root()

# Access configuration values
num_items = config['NUM_<SOURCE>_ITEMS']  # Number of items to scrape
output_dir = os.path.join(repo_root, config['TEXTS_DIR'], config['<SOURCE>_SUBDIR'])
```

Add your configuration keys to `config/application.config`:
```bash
# My Custom Scraper Settings
NUM_MYSOURCE_ITEMS=10
MYSOURCE_SUBDIR=mysource
MYSOURCE_API_URL=https://api.example.com
```

### 5. Progress Reporting

Scrapers **MUST** output progress information using the `output_progress()` function for real-time GUI/TUI updates:

```python
from utils.common import output_progress

# Output format: output_progress(successful, failures, processed, total, current_item)

# At start
output_progress(0, 0, 0, total_items, "Starting scraper")

# During processing
for i, item in enumerate(items):
    output_progress(successful, failures, i, total_items, f"Processing: {item_name}")
    # ... process item ...

# At end
output_progress(successful, failures, total_items, total_items, "Complete")
```

**Progress Line Format:**
```
PROGRESS|successful|failures|processed|total|current_item
```

Example:
```
PROGRESS|5|1|6|10|Fetching article: How to Build a Scraper
```

### 6. Main Function

All scrapers must have a `main()` function that:
1. Loads configuration
2. Outputs initial progress
3. Fetches content
4. Creates EPUB files
5. Outputs final progress
6. Returns success/failure counts

```python
def main():
    """Main function to orchestrate the scraping and EPUB creation."""
    print("=" * 60)
    print("My Custom Scraper")
    print("=" * 60)

    # Load configuration
    config = get_config()
    repo_root = get_repo_root()

    num_items = config['NUM_MYSOURCE_ITEMS']
    successful = 0
    failures = 0

    # Output directory
    output_dir = os.path.join(repo_root, config['TEXTS_DIR'], config['MYSOURCE_SUBDIR'])
    os.makedirs(output_dir, exist_ok=True)

    # Output initial progress
    output_progress(0, 0, 0, num_items, "Starting My Custom Scraper")

    # Fetch items
    items = fetch_items(num_items, config)

    if not items:
        print("Error: No items found!")
        output_progress(0, num_items, num_items, num_items, "Error: No items found")
        return

    # Create EPUBs
    for i, item in enumerate(items):
        output_progress(successful, failures, i, len(items), f"Creating: {item['title'][:50]}")
        try:
            create_epub(item, output_dir)
            successful += 1
        except Exception as e:
            print(f"Error: {e}")
            failures += 1

    # Final progress
    output_progress(successful, failures, successful + failures, len(items), "Complete")

    print("\n" + "=" * 60)
    print("Done!")
    print(f"Successful: {successful} | Failed: {failures}")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

### 7. EPUB Creation

Use the `ebooklib` library to create EPUBs:

```python
from ebooklib import epub

def create_epub(item, output_dir):
    """Create an EPUB file for a single item."""
    book = epub.EpubBook()

    # Set metadata
    book.set_identifier(f'unique_id_{item["id"]}')
    book.set_title(item['title'])
    book.set_language('en')
    book.add_author(item.get('author', 'Unknown'))

    # Create chapter
    chapter = epub.EpubHtml(
        title=item['title'],
        file_name='content.xhtml',
        lang='en'
    )

    # Set content
    chapter.content = f'''
    <html>
    <head>
        <title>{item['title']}</title>
    </head>
    <body>
        <h1>{item['title']}</h1>
        {item['content']}
    </body>
    </html>
    '''

    # Add chapter to book
    book.add_item(chapter)

    # Define Table of Contents
    book.toc = (chapter,)

    # Add navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Define spine
    book.spine = ['nav', chapter]

    # Write EPUB file
    output_file = os.path.join(output_dir, f"{sanitize_filename(item['title'])}.epub")
    epub.write_epub(output_file, book, {})
    return output_file
```

### 8. Output Location

EPUBs should be written to:
```
{TEXTS_DIR}/{YOUR_SOURCE_SUBDIR}/filename.epub
```

Default: `./texts/yoursource/filename.epub`

## Full Example Template

```python
#!/usr/bin/env python3
"""
Scraper for Example Source - fetches articles and converts to EPUB.
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
from ebooklib import epub

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.common import suppress_urllib3_warning, output_progress
from config_reader import get_config, get_repo_root

# Suppress urllib3 warning
suppress_urllib3_warning()


def fetch_items(num_items, config):
    """Fetch items from the source."""
    # Implement your fetching logic
    items = []
    # ... fetch from API or web scraping ...
    return items


def sanitize_filename(title, max_length=50):
    """Convert title to safe filename."""
    safe = title.replace('/', '-').replace('\\', '-').replace(':', '-')
    safe = safe.replace('?', '').replace('*', '').replace('"', '')
    safe = safe.replace('<', '').replace('>', '').replace('|', '')
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip()
    return safe


def create_epub(item, output_dir):
    """Create an EPUB file for a single item."""
    book = epub.EpubBook()

    book.set_identifier(f'example_{item["id"]}')
    book.set_title(item['title'])
    book.set_language('en')
    book.add_author(item.get('author', 'Unknown'))

    chapter = epub.EpubHtml(
        title=item['title'],
        file_name='content.xhtml',
        lang='en'
    )

    chapter.content = f'''
    <html>
    <head>
        <title>{item['title']}</title>
    </head>
    <body>
        <h1>{item['title']}</h1>
        {item['content']}
    </body>
    </html>
    '''

    book.add_item(chapter)
    book.toc = (chapter,)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav', chapter]

    output_file = os.path.join(output_dir, f"{sanitize_filename(item['title'])}.epub")
    epub.write_epub(output_file, book, {})
    return output_file


def main():
    """Main function."""
    print("=" * 60)
    print("Example Scraper")
    print("=" * 60)

    config = get_config()
    repo_root = get_repo_root()

    num_items = config.get('NUM_EXAMPLE_ITEMS', 10)
    successful = 0
    failures = 0

    output_dir = os.path.join(repo_root, config['TEXTS_DIR'], config.get('EXAMPLE_SUBDIR', 'example'))
    os.makedirs(output_dir, exist_ok=True)

    output_progress(0, 0, 0, num_items, "Starting Example Scraper")

    items = fetch_items(num_items, config)

    if not items:
        print("Error: No items found!")
        output_progress(0, num_items, num_items, num_items, "Error: No items found")
        return

    for i, item in enumerate(items):
        output_progress(successful, failures, i, len(items), f"Creating: {item['title'][:50]}")
        try:
            create_epub(item, output_dir)
            successful += 1
        except Exception as e:
            print(f"Error creating EPUB: {e}")
            failures += 1

    output_progress(successful, failures, successful + failures, len(items), "Complete")

    print("\n" + "=" * 60)
    print("Done!")
    print(f"Successful: {successful} | Failed: {failures}")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

## Testing Your Scraper

1. **Command Line Test:**
   ```bash
   python3 bin/scrapers/scrape_example_to_epub.py
   ```

2. **Check Progress Output:**
   - Verify `PROGRESS|...` lines appear
   - Confirm format is correct: `PROGRESS|successful|failures|processed|total|message`

3. **GUI/TUI Integration:**
   - The GUI and TUI will automatically discover your scraper
   - It will appear in the Generate tab with a checkbox
   - Name is derived from filename: `scrape_example_to_epub.py` → "Example"

## Best Practices

1. **Error Handling:** Always use try/except and increment failure count
2. **Logging:** Print informative messages for debugging
3. **Configuration:** Use config file instead of hardcoding values
4. **Progress Updates:** Update progress frequently for responsive UI
5. **Filename Safety:** Sanitize filenames to avoid filesystem issues
6. **Respect Rate Limits:** Add delays between requests if scraping websites
7. **Test Thoroughly:** Test with various inputs and edge cases

## Dependencies

Add any additional dependencies to `requirements.txt`:
```bash
echo "your-library==1.2.3" >> requirements.txt
pip install -r requirements.txt
```

## Troubleshooting

**Scraper not appearing in GUI/TUI:**
- Check filename follows pattern: `scrape_*_to_epub.py`
- Verify file is in `bin/scrapers/` directory
- Ensure file is executable: `chmod +x bin/scrapers/scrape_*.py`

**Progress not updating:**
- Verify you're calling `output_progress()` with correct parameters
- Ensure you imported from `utils.common`
- Check flush=True is used (handled by output_progress function)

**Configuration not loading:**
- Verify config keys exist in `config/application.config`
- Use `config.get('KEY', default_value)` for optional values
- Check no spaces around `=` in config file

## Examples

See the existing scrapers for complete examples:
- `bin/scrapers/scrape_hn_to_epub.py` - Hacker News (uses API)
- `bin/scrapers/scrape_hcr_to_epub.py` - Heather Cox Richardson (web scraping)
- `bin/scrapers/scrape_hackaday_to_epub.py` - Hackaday blog (WordPress-based site)

## Implementation Notes

These notes document issues discovered while implementing scrapers:

### WordPress-based Sites (e.g., Hackaday)

1. **Date extraction**: WordPress sites often use `<a>` links to date archives instead of `<time>` elements. Use regex to match date URLs:
   ```python
   import re
   date_link = article.find("a", href=re.compile(r"example\.com/\d{4}/\d{2}/\d{2}/$"))
   if date_link:
       date = date_link.get_text(strip=True)
       # Fallback to title attribute if text is empty
       if not date and date_link.get("title"):
           date = date_link.get("title").split(" - ")[0]
   ```

2. **Content extraction**: WordPress uses `.entry-content` class for article body. Remove these elements to avoid noise:
   - `.comments-area`, `.related-posts`, `.sharedaddy`
   - `[class*="ad-"]`, `[id*="ad-"]`
   - `.widget`, `.jp-relatedposts`, `.author-bio`

3. **Pagination**: WordPress blogs paginate at `/page/N/`. Implement page iteration with a safety limit:
   ```python
   page = 1
   while len(articles) < num_articles and page <= 10:
       url = f"{blog_url}page/{page}/" if page > 1 else blog_url
       # ... fetch and parse ...
       page += 1
   ```

### General Best Practices Learned

1. **Always test URL patterns**: Date/author/category links may use full URLs (`https://...`) rather than relative paths (`/...`)

2. **Handle missing metadata gracefully**: Not all articles have all fields. Use defaults:
   ```python
   author = "Site Name"  # Default
   author_elem = article.find("a", href=lambda x: x and "/author/" in x)
   if author_elem:
       author = author_elem.get_text(strip=True)
   ```

3. **Filter nested elements**: When extracting content, filter out nested elements to avoid duplicates:
   ```python
   elements = content.find_all(["p", "h1", "h2", ...])
   top_level = [e for e in elements if not any(e in o.descendants for o in elements if o != e)]
   ```
