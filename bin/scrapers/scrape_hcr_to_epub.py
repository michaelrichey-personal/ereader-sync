#!/usr/bin/env python3
"""
Script to scrape the last 5 text entries from Heather Cox Richardson's Substack
and generate an EPUB file with table of contents.
"""

import os
import re
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from ebooklib import epub

from bin.config_reader import get_config, get_repo_root
from bin.utils.common import output_progress, suppress_urllib3_warning

# Suppress urllib3 warning
suppress_urllib3_warning()


def is_date_title(title):
    """Check if a title is formatted as a date (her daily letters)."""
    # Pattern matches: "Month Day, Year" (e.g., "December 2, 2025")
    date_pattern = r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}$"
    return re.match(date_pattern, title) is not None


def date_title_to_filename(title):
    """Convert date title to filename format hcr-YYYY-MM-DD.epub"""
    try:
        # Parse the date from title like "December 2, 2025"
        date_obj = datetime.strptime(title, "%B %d, %Y")
        # Format as hcr-YYYY-MM-DD.epub
        return f"hcr-{date_obj.strftime('%Y-%m-%d')}.epub"
    except Exception as e:
        print(f"Error converting date '{title}': {e}")
        # Fallback to sanitized title
        safe_title = title.replace(" ", "-").replace(",", "")
        return f"hcr-{safe_title}.epub"


def get_recent_posts(num_posts, archive_url, min_word_count, max_candidates):
    """Fetch the most recent full letter posts from the archive page."""

    print(f"Fetching archive from {archive_url}...")
    response = requests.get(archive_url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    # Find all post links in the archive
    candidates = []

    # Substack archive posts are typically in divs with class containing 'post'
    # Let's look for links to posts in the archive
    post_links = soup.find_all("a", href=re.compile(r"/p/[^/]+$"))

    seen_urls = set()
    for link in post_links:
        url = link.get("href")
        if not url:
            continue

        # Make absolute URL
        if url.startswith("/"):
            url = f"https://heathercoxrichardson.substack.com{url}"

        # Skip duplicates
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Get title from link text or nearby elements
        title = link.get_text(strip=True)
        if not title:
            continue

        # Only include posts with date-formatted titles (her daily letters)
        if not is_date_title(title):
            continue

        candidates.append({"url": url, "title": title})

        # Get enough candidates to ensure we find enough full letters
        if len(candidates) >= max_candidates:
            break

    # Filter for full letters and ensure unique dates
    posts = []
    seen_dates = set()

    print("\nChecking candidates for full letters...")
    for candidate in candidates:
        # Skip if we already have a post for this date
        if candidate["title"] in seen_dates:
            print(f"  Skipping duplicate date: {candidate['title']}")
            continue

        # Check if it's a full letter (not podcast/video/short post)
        print(f"  Checking: {candidate['title']}")
        if is_full_letter(candidate["url"], min_word_count):
            posts.append(candidate)
            seen_dates.add(candidate["title"])
            print("    ✓ Full letter found")

            if len(posts) >= num_posts:
                break
        else:
            print("    ✗ Not a full letter (podcast/video/short post)")

    return posts


def is_full_letter(post_url, min_word_count):
    """Check if a post is a full letter (not a podcast/video/short post)."""
    try:
        response = requests.get(post_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Check for podcast indicator
        if soup.find("audio") or soup.find(class_=re.compile(r"podcast", re.I)):
            return False

        # Check for video indicator
        if soup.find("video") or soup.find(class_=re.compile(r"video", re.I)):
            return False

        # Find the main content
        content_div = soup.find("div", class_=re.compile(r"(body|post-content|available-content)"))
        if not content_div:
            content_div = soup.find("article")

        if not content_div:
            return False

        # Check if content is substantial (full letters are typically 1000+ words)
        text_content = content_div.get_text(strip=True)
        word_count = len(text_content.split())

        # Full letters typically have min_word_count+ words
        return word_count > min_word_count

    except Exception as e:
        print(f"Error checking post {post_url}: {e}")
        return False


def get_post_content(post_url):
    """Fetch the full content of a single post."""
    print(f"Fetching post: {post_url}")
    response = requests.get(post_url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    # Find the main post content
    # Substack posts are typically in a div with class 'body' or 'post-content'
    content_div = soup.find("div", class_=re.compile(r"(body|post-content|available-content)"))

    if not content_div:
        # Try alternative selectors
        content_div = soup.find("article")

    if not content_div:
        print(f"Warning: Could not find content for {post_url}")
        return "<p>Content could not be extracted.</p>"

    # Get the HTML content
    content_html = str(content_div)

    return content_html


def create_epub_for_post(post, output_path):
    """Create an individual EPUB file for a single post."""
    # Create EPUB book
    book = epub.EpubBook()

    # Set metadata
    book.set_identifier(f"hcr_letter_{post['title']}")
    book.set_title(f"Letters from an American - {post['title']}")
    book.set_language("en")
    book.add_author("Heather Cox Richardson")

    # Create chapter
    chapter = epub.EpubHtml(title=post["title"], file_name="content.xhtml", lang="en")

    # Set content
    chapter.content = f"""
    <html>
    <head>
        <title>{post["title"]}</title>
    </head>
    <body>
        <h1>{post["title"]}</h1>
        {post["content"]}
    </body>
    </html>
    """

    # Add chapter to book
    book.add_item(chapter)

    # Define Table of Contents
    book.toc = (chapter,)

    # Add navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Define spine
    book.spine = ["nav", chapter]

    # Write EPUB file
    epub.write_epub(output_path, book, {})
    return output_path


def main():
    """Main function to orchestrate the scraping and EPUB creation."""
    print("=" * 60)
    print("Heather Cox Richardson Substack to EPUB Converter")
    print("=" * 60)

    # Load configuration
    config = get_config()
    repo_root = get_repo_root()

    num_posts = config["NUM_HCR_POSTS"]
    successful = 0
    failures = 0

    # Output directory (relative to repository root)
    output_dir = os.path.join(repo_root, config["TEXTS_DIR"], config["HCR_SUBDIR"])

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Output initial progress
    output_progress(0, 0, 0, num_posts, "Starting HCR letter scraper")

    # Get recent posts with config values
    posts = get_recent_posts(
        num_posts=num_posts,
        archive_url=config["HCR_ARCHIVE_URL"],
        min_word_count=config["MIN_LETTER_WORD_COUNT"],
        max_candidates=config["MAX_HCR_CANDIDATES"],
    )

    if not posts:
        print("Error: No posts found!")
        output_progress(0, num_posts, num_posts, num_posts, "Error: No posts found")
        return

    print(f"\nFound {len(posts)} posts:")
    for i, post in enumerate(posts, 1):
        print(f"{i}. {post['title']}")

    # Fetch content for each post
    print("\nFetching post contents...")
    for i, post in enumerate(posts):
        output_progress(successful, failures, i, len(posts), f"Fetching content: {post['title']}")
        try:
            post["content"] = get_post_content(post["url"])
        except Exception as e:
            print(f"  Error fetching content for {post['title']}: {e}")
            failures += 1
            continue

    # Create individual EPUBs
    print("\nCreating individual EPUBs...")
    created_files = []

    for i, post in enumerate(posts):
        # Generate filename from date
        filename = date_title_to_filename(post["title"])
        output_file = os.path.join(output_dir, filename)

        output_progress(
            successful, failures, successful + failures, len(posts), f"Creating EPUB: {filename}"
        )

        try:
            # Create EPUB
            create_epub_for_post(post, output_file)
            created_files.append(output_file)
            successful += 1
            print(f"  Created: {filename}")
        except Exception as e:
            print(f"  Error creating EPUB for {post['title']}: {e}")
            failures += 1

    # Final progress
    output_progress(successful, failures, successful + failures, len(posts), "Complete")

    print("\n" + "=" * 60)
    print("Done!")
    print(f"Created {len(created_files)} EPUBs in: {output_dir}")
    print(f"Successful: {successful} | Failed: {failures}")

    # Try to copy to SD card
    sd_card_path = config["SD_CARD_PATH"]
    if os.path.exists(sd_card_path) and os.path.isdir(sd_card_path):
        try:
            import shutil

            # Create hcr directory on SD card
            sd_hcr_dir = os.path.join(sd_card_path, config["HCR_SUBDIR"])
            os.makedirs(sd_hcr_dir, exist_ok=True)

            # Copy all EPUBs
            for epub_file in created_files:
                filename = os.path.basename(epub_file)
                sd_output = os.path.join(sd_hcr_dir, filename)
                shutil.copy2(epub_file, sd_output)

            print(f"All EPUBs copied to SD card: {sd_hcr_dir}")
        except Exception as e:
            print(f"Warning: Could not copy to SD card: {e}")
    else:
        print("Note: SD card not found, skipping copy to SD card")

    print("=" * 60)


if __name__ == "__main__":
    main()
