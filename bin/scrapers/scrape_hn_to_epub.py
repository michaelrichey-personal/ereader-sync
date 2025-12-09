#!/usr/bin/env python3
"""
Script to scrape the top 20 posts from Hacker News
and generate an EPUB file with table of contents.
"""

import os
import sys

import requests
from bs4 import BeautifulSoup
from ebooklib import epub

from bin.config_reader import get_config, get_repo_root
from bin.utils.common import output_progress, suppress_urllib3_warning

# Suppress urllib3 warning
suppress_urllib3_warning()


def get_top_stories(num_stories, api_base):
    """Fetch the top stories from Hacker News API."""
    print("Fetching top stories from Hacker News...")

    # Get top story IDs
    response = requests.get(f"{api_base}/topstories.json", timeout=30)
    response.raise_for_status()
    story_ids = response.json()[:num_stories]

    stories = []

    for story_id in story_ids:
        # Get story details
        story_response = requests.get(f"{api_base}/item/{story_id}.json", timeout=30)
        story_response.raise_for_status()
        story_data = story_response.json()

        # Skip if no URL (e.g., Ask HN posts)
        if "url" not in story_data:
            print(f"  Skipping: {story_data.get('title', 'No title')} (no URL)")
            continue

        stories.append(
            {
                "title": story_data.get("title", "No title"),
                "url": story_data.get("url"),
                "by": story_data.get("by", "unknown"),
                "score": story_data.get("score", 0),
                "id": story_id,
            }
        )

        print(f"  {len(stories)}. {story_data.get('title', 'No title')}")

        if len(stories) >= num_stories:
            break

    return stories


def fetch_article_content(url, title, fetch_timeout):
    """Fetch and extract the main content from an article URL."""
    try:
        print(f"Fetching: {title[:60]}...")
        response = requests.get(url, timeout=fetch_timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()

        # Try to find the main content
        # Look for common article containers
        content = None
        for selector in [
            "article",
            "main",
            '[role="main"]',
            ".post-content",
            ".article-content",
            ".entry-content",
        ]:
            content = soup.select_one(selector)
            if content:
                break

        # If no specific container found, try to get the body
        if not content:
            content = soup.find("body")

        if not content:
            return f"<p>Could not extract content from: <a href='{url}'>{url}</a></p>"

        # Extract text content, preserving paragraph structure
        # Find all potential content elements
        all_elements = content.find_all(
            ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"]
        )

        # Filter out elements that are descendants of other matched elements
        # This prevents duplicates from nested structures (e.g., <blockquote><p>...</p></blockquote>)
        top_level_elements = []
        for element in all_elements:
            # Check if this element is a descendant of any other matched element
            is_nested = False
            for other in all_elements:
                if other != element and element in other.descendants:
                    is_nested = True
                    break
            if not is_nested:
                top_level_elements.append(element)

        paragraphs = []
        for element in top_level_elements:
            text = element.get_text(strip=True)
            if text:  # Only include non-empty paragraphs
                # Wrap in appropriate HTML tag
                if element.name.startswith("h"):
                    paragraphs.append(f"<{element.name}>{text}</{element.name}>")
                elif element.name == "li":
                    paragraphs.append(f"<li>{text}</li>")
                elif element.name == "blockquote":
                    paragraphs.append(f"<blockquote><p>{text}</p></blockquote>")
                else:
                    paragraphs.append(f"<p>{text}</p>")

        # If no paragraphs found, fall back to all text
        if not paragraphs:
            text = content.get_text(separator="\n\n", strip=True)
            paragraphs = [f"<p>{para.strip()}</p>" for para in text.split("\n\n") if para.strip()]

        content_html = "\n".join(paragraphs)
        return content_html

    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return f"<p>Error loading content. View original: <a href='{url}'>{url}</a></p><p>Error: {str(e)}</p>"


def sanitize_filename(title, max_length):
    """Convert a title into a safe filename."""
    # Remove or replace unsafe characters
    safe_title = title.replace("/", "-").replace("\\", "-").replace(":", "-")
    safe_title = safe_title.replace("?", "").replace("*", "").replace('"', "")
    safe_title = safe_title.replace("<", "").replace(">", "").replace("|", "")

    # Truncate if too long
    if len(safe_title) > max_length:
        safe_title = safe_title[:max_length].rstrip()

    return safe_title


def create_epub_for_story(story, output_path):
    """Create an individual EPUB file for a single story."""
    # Create EPUB book
    book = epub.EpubBook()

    # Set metadata
    book.set_identifier(f"hackernews_story_{story['id']}")
    book.set_title(story["title"])
    book.set_language("en")
    book.add_author(f"{story['by']} (via Hacker News)")

    # Create chapter
    chapter = epub.EpubHtml(title=story["title"], file_name="content.xhtml", lang="en")

    # Set content
    chapter.content = f"""
    <html>
    <head>
        <title>{story["title"]}</title>
    </head>
    <body>
        <h1>{story["title"]}</h1>
        <p><strong>Score:</strong> {story["score"]} points | <strong>Posted by:</strong> {story["by"]}</p>
        <p><strong>Original URL:</strong> <a href="{story["url"]}">{story["url"]}</a></p>
        <p><strong>Discussion:</strong> <a href="https://news.ycombinator.com/item?id={story["id"]}">View on Hacker News</a></p>
        <hr/>
        {story["content"]}
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
    print("Hacker News Top Stories to EPUB Converter")
    print("=" * 60)

    # Load configuration
    config = get_config()
    repo_root = get_repo_root()

    num_stories = config["NUM_HN_STORIES"]
    successful = 0
    failures = 0

    # Output directory (relative to repository root)
    output_dir = os.path.join(repo_root, config["TEXTS_DIR"])
    hn_dir = os.path.join(output_dir, config["HACKERNEWS_SUBDIR"])

    # Ensure output directory exists
    os.makedirs(hn_dir, exist_ok=True)

    # Output initial progress
    output_progress(0, 0, 0, num_stories, "Starting Hacker News scraper")

    # Get top stories
    stories = get_top_stories(num_stories=num_stories, api_base=config["HN_API_BASE"])

    if not stories:
        print("Error: No stories found!")
        output_progress(0, num_stories, num_stories, num_stories, "Error: No stories found")
        return

    print(f"\nFound {len(stories)} stories with URLs")

    # Fetch content for each story
    print("\nFetching article contents...")
    for i, story in enumerate(stories):
        output_progress(successful, failures, i, len(stories), f"Fetching: {story['title'][:50]}")
        try:
            story["content"] = fetch_article_content(
                story["url"], story["title"], config["HN_FETCH_TIMEOUT"]
            )
        except Exception as e:
            print(f"  Error fetching content for {story['title']}: {e}")
            failures += 1
            continue

    # Create individual EPUBs
    print("\nCreating individual EPUBs...")
    created_files = []

    for i, story in enumerate(stories):
        # Create safe filename from title
        safe_title = sanitize_filename(story["title"], config["HN_MAX_FILENAME_LENGTH"])
        filename = f"{safe_title}.epub"
        output_file = os.path.join(hn_dir, filename)

        output_progress(
            successful,
            failures,
            successful + failures,
            len(stories),
            f"Creating EPUB: {filename[:50]}",
        )

        try:
            # Create EPUB
            create_epub_for_story(story, output_file)
            created_files.append(output_file)
            successful += 1
            print(f"  {i + 1}. Created: {filename}")
        except Exception as e:
            print(f"  Error creating EPUB for {story['title']}: {e}")
            failures += 1

    # Final progress
    output_progress(successful, failures, successful + failures, len(stories), "Complete")

    print("\n" + "=" * 60)
    print("Done!")
    print(f"Created {len(created_files)} EPUBs in: {hn_dir}")
    print(f"Successful: {successful} | Failed: {failures}")

    # Try to copy to SD card
    sd_card_path = config["SD_CARD_PATH"]
    if os.path.exists(sd_card_path) and os.path.isdir(sd_card_path):
        try:
            import shutil

            # Create hackernews directory on SD card
            sd_hn_dir = os.path.join(sd_card_path, "hackernews")
            os.makedirs(sd_hn_dir, exist_ok=True)

            # Copy all EPUBs
            for epub_file in created_files:
                filename = os.path.basename(epub_file)
                sd_output = os.path.join(sd_hn_dir, filename)
                shutil.copy2(epub_file, sd_output)

            print(f"All EPUBs copied to SD card: {sd_hn_dir}")
        except Exception as e:
            print(f"Warning: Could not copy to SD card: {e}")
    else:
        print("Note: SD card not found, skipping copy to SD card")

    print("=" * 60)


if __name__ == "__main__":
    main()
