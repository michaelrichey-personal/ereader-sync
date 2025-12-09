#!/usr/bin/env python3
"""
Scraper for Hackaday.com blog - fetches recent articles and converts to EPUB.
"""

import os
import re
import sys

import requests
from bs4 import BeautifulSoup
from ebooklib import epub

from bin.config_reader import get_config, get_repo_root
from bin.utils.common import output_progress, suppress_urllib3_warning

# Suppress urllib3 warning
suppress_urllib3_warning()


def get_blog_articles(num_articles, blog_url, timeout):
    """Fetch article links from Hackaday blog page."""
    print(f"Fetching articles from {blog_url}...")

    articles = []
    page = 1

    while len(articles) < num_articles:
        # Build page URL
        if page == 1:
            url = blog_url
        else:
            url = f"{blog_url}page/{page}/"

        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
        except Exception as e:
            print(f"  Error fetching page {page}: {e}")
            break

        soup = BeautifulSoup(response.content, "html.parser")

        # Find all article elements
        article_elements = soup.find_all("article")

        if not article_elements:
            print(f"  No articles found on page {page}")
            break

        for article in article_elements:
            if len(articles) >= num_articles:
                break

            # Find title and link - look for heading with link
            title_elem = article.find(["h1", "h2", "h3"])
            if not title_elem:
                continue

            link_elem = title_elem.find("a")
            if not link_elem:
                # Try finding link directly in article
                link_elem = article.find("a", href=True)
                if not link_elem:
                    continue

            title = link_elem.get_text(strip=True)
            url = link_elem.get("href")

            if not title or not url:
                continue

            # Skip if URL doesn't look like an article
            if "/category/" in url or "/tag/" in url or "/author/" in url:
                continue

            # Find author
            author = "Hackaday"
            author_elem = article.find("a", href=lambda x: x and "/author/" in x)
            if author_elem:
                author = author_elem.get_text(strip=True)

            # Find date - Hackaday uses links with date paths like /2025/12/08/
            date = ""
            date_elem = article.find("time")
            if date_elem:
                date = date_elem.get_text(strip=True)
            else:
                # Try finding date link (format: https://hackaday.com/YYYY/MM/DD/)
                date_link = article.find("a", href=re.compile(r"hackaday\.com/\d{4}/\d{2}/\d{2}/$"))
                if date_link:
                    date = date_link.get_text(strip=True)
                    # If no text, try title attribute
                    if not date and date_link.get("title"):
                        date = date_link.get("title").split(" - ")[0]

            articles.append(
                {
                    "title": title,
                    "url": url,
                    "author": author,
                    "date": date,
                    "id": url.rstrip("/").split("/")[-1],  # Use slug as ID
                }
            )

            print(f"  {len(articles)}. {title[:60]}")

        page += 1

        # Safety limit to avoid infinite loops
        if page > 10:
            break

    return articles


def fetch_article_content(url, title, timeout):
    """Fetch and extract the main content from an article URL."""
    try:
        print(f"  Fetching: {title[:50]}...")
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Remove unwanted elements
        for selector in [
            "script",
            "style",
            "nav",
            "header",
            "footer",
            "aside",
            ".comments-area",
            ".related-posts",
            ".sharedaddy",
            ".jp-relatedposts",
            ".post-nav",
            ".author-bio",
            '[class*="ad-"]',
            '[id*="ad-"]',
            ".widget",
        ]:
            for elem in soup.select(selector):
                elem.decompose()

        # Try to find main content using common WordPress selectors
        content = None
        for selector in [
            ".entry-content",
            ".post-content",
            "article .content",
            "article",
            ".post",
            "main",
        ]:
            content = soup.select_one(selector)
            if content:
                break

        if not content:
            content = soup.find("body")

        if not content:
            return f"<p>Could not extract content from: <a href='{url}'>{url}</a></p>"

        # Extract content elements
        elements = content.find_all(
            ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre", "code"]
        )

        # Filter out nested elements to avoid duplicates
        top_level_elements = []
        for element in elements:
            is_nested = False
            for other in elements:
                if other != element and element in other.descendants:
                    is_nested = True
                    break
            if not is_nested:
                top_level_elements.append(element)

        paragraphs = []
        for element in top_level_elements:
            text = element.get_text(strip=True)
            if not text:
                continue

            if element.name.startswith("h"):
                paragraphs.append(f"<{element.name}>{text}</{element.name}>")
            elif element.name == "li":
                paragraphs.append(f"<li>{text}</li>")
            elif element.name == "blockquote":
                paragraphs.append(f"<blockquote><p>{text}</p></blockquote>")
            elif element.name in ["pre", "code"]:
                paragraphs.append(f"<pre><code>{text}</code></pre>")
            else:
                paragraphs.append(f"<p>{text}</p>")

        if not paragraphs:
            text = content.get_text(separator="\n\n", strip=True)
            paragraphs = [f"<p>{para.strip()}</p>" for para in text.split("\n\n") if para.strip()]

        return "\n".join(paragraphs)

    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return f"<p>Error loading content. View original: <a href='{url}'>{url}</a></p><p>Error: {str(e)}</p>"


def sanitize_filename(title, max_length):
    """Convert a title into a safe filename."""
    safe_title = title.replace("/", "-").replace("\\", "-").replace(":", "-")
    safe_title = safe_title.replace("?", "").replace("*", "").replace('"', "")
    safe_title = safe_title.replace("<", "").replace(">", "").replace("|", "")

    if len(safe_title) > max_length:
        safe_title = safe_title[:max_length].rstrip()

    return safe_title


def create_epub_for_article(article, output_path):
    """Create an individual EPUB file for a single article."""
    book = epub.EpubBook()

    # Set metadata
    book.set_identifier(f"hackaday_{article['id']}")
    book.set_title(article["title"])
    book.set_language("en")
    book.add_author(article["author"])

    # Create chapter
    chapter = epub.EpubHtml(title=article["title"], file_name="content.xhtml", lang="en")

    # Set content
    chapter.content = f"""
    <html>
    <head>
        <title>{article["title"]}</title>
    </head>
    <body>
        <h1>{article["title"]}</h1>
        <p><strong>Author:</strong> {article["author"]} | <strong>Date:</strong> {article["date"]}</p>
        <p><strong>Original URL:</strong> <a href="{article["url"]}">{article["url"]}</a></p>
        <hr/>
        {article["content"]}
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
    print("Hackaday Blog to EPUB Converter")
    print("=" * 60)

    # Load configuration
    config = get_config()
    repo_root = get_repo_root()

    num_articles = config.get("NUM_HACKADAY_ARTICLES", 10)
    blog_url = config.get("HACKADAY_BLOG_URL", "https://hackaday.com/blog/")
    fetch_timeout = config.get("HACKADAY_FETCH_TIMEOUT", 15)
    max_filename_length = config.get("HACKADAY_MAX_FILENAME_LENGTH", 50)

    successful = 0
    failures = 0

    # Output directory
    output_dir = os.path.join(
        repo_root, config["TEXTS_DIR"], config.get("HACKADAY_SUBDIR", "hackaday")
    )
    os.makedirs(output_dir, exist_ok=True)

    # Output initial progress
    output_progress(0, 0, 0, num_articles, "Starting Hackaday scraper")

    # Get articles
    articles = get_blog_articles(num_articles, blog_url, fetch_timeout)

    if not articles:
        print("Error: No articles found!")
        output_progress(0, num_articles, num_articles, num_articles, "Error: No articles found")
        return

    print(f"\nFound {len(articles)} articles")

    # Fetch content for each article
    print("\nFetching article contents...")
    for i, article in enumerate(articles):
        output_progress(
            successful, failures, i, len(articles), f"Fetching: {article['title'][:50]}"
        )
        try:
            article["content"] = fetch_article_content(
                article["url"], article["title"], fetch_timeout
            )
        except Exception as e:
            print(f"  Error fetching content for {article['title']}: {e}")
            article["content"] = f"<p>Error: {e}</p>"

    # Create individual EPUBs
    print("\nCreating EPUBs...")
    created_files = []

    for i, article in enumerate(articles):
        safe_title = sanitize_filename(article["title"], max_filename_length)
        filename = f"{safe_title}.epub"
        output_file = os.path.join(output_dir, filename)

        output_progress(
            successful,
            failures,
            successful + failures,
            len(articles),
            f"Creating EPUB: {filename[:50]}",
        )

        try:
            create_epub_for_article(article, output_file)
            created_files.append(output_file)
            successful += 1
            print(f"  {i + 1}. Created: {filename}")
        except Exception as e:
            print(f"  Error creating EPUB for {article['title']}: {e}")
            failures += 1

    # Final progress
    output_progress(successful, failures, successful + failures, len(articles), "Complete")

    print("\n" + "=" * 60)
    print("Done!")
    print(f"Created {len(created_files)} EPUBs in: {output_dir}")
    print(f"Successful: {successful} | Failed: {failures}")
    print("=" * 60)


if __name__ == "__main__":
    main()
