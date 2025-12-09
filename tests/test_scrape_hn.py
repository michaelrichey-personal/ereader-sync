#!/usr/bin/env python3
"""Tests for the scrape_hn_to_epub module."""
import os
import sys
import tempfile
from unittest.mock import Mock, patch
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bin.scrapers.scrape_hn_to_epub import (
    get_top_stories,
    fetch_article_content,
    sanitize_filename,
    create_epub_for_story,
)


def test_get_top_stories():
    """Test fetching top stories from HN API."""
    # Mock API responses
    mock_topstories_response = Mock()
    mock_topstories_response.json.return_value = [1, 2, 3, 4, 5]
    mock_topstories_response.raise_for_status = Mock()

    mock_story1 = Mock()
    mock_story1.json.return_value = {
        "id": 1,
        "title": "Test Story 1",
        "url": "http://test.com/1",
        "by": "user1",
        "score": 100,
    }
    mock_story1.raise_for_status = Mock()

    mock_story2 = Mock()
    mock_story2.json.return_value = {
        "id": 2,
        "title": "Test Story 2",
        "url": "http://test.com/2",
        "by": "user2",
        "score": 200,
    }
    mock_story2.raise_for_status = Mock()

    # Story without URL (Ask HN)
    mock_story3 = Mock()
    mock_story3.json.return_value = {
        "id": 3,
        "title": "Ask HN: Something",
        "by": "user3",
        "score": 50,
    }
    mock_story3.raise_for_status = Mock()

    with patch("requests.get") as mock_get:
        mock_get.side_effect = [
            mock_topstories_response,
            mock_story1,
            mock_story2,
            mock_story3,
        ]

        stories = get_top_stories(2, "https://hacker-news.firebaseio.com/v0")

        # Should get 2 stories with URLs
        assert len(stories) == 2
        assert stories[0]["title"] == "Test Story 1"
        assert stories[1]["title"] == "Test Story 2"


def test_fetch_article_content():
    """Test fetching article content from URL."""
    mock_html = """
    <html>
        <head><title>Test Article</title></head>
        <body>
            <article>
                <h1>Article Title</h1>
                <p>This is paragraph 1.</p>
                <p>This is paragraph 2.</p>
            </article>
        </body>
    </html>
    """

    mock_response = Mock()
    mock_response.content = mock_html.encode()
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        content = fetch_article_content("http://test.com/article", "Test", 10)

        assert "Article Title" in content
        assert "paragraph 1" in content
        assert "paragraph 2" in content


def test_fetch_article_content_with_main():
    """Test fetching content with <main> tag."""
    mock_html = """
    <html>
        <body>
            <nav>Navigation</nav>
            <main>
                <p>Main content here</p>
            </main>
            <footer>Footer</footer>
        </body>
    </html>
    """

    mock_response = Mock()
    mock_response.content = mock_html.encode()
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        content = fetch_article_content("http://test.com/article", "Test", 10)

        assert "Main content" in content
        assert "Navigation" not in content  # nav removed
        assert "Footer" not in content  # footer removed


def test_fetch_article_content_error():
    """Test handling errors when fetching articles."""
    with patch("requests.get", side_effect=Exception("Network error")):
        content = fetch_article_content("http://test.com/article", "Test", 10)

        # Should return error message
        assert "Error loading content" in content
        assert "Network error" in content


def test_sanitize_filename():
    """Test sanitizing filenames."""
    assert sanitize_filename("Normal Title", 50) == "Normal Title"
    assert sanitize_filename("Title/With\\Slashes", 50) == "Title-With-Slashes"
    assert sanitize_filename("Title:With?Special*Chars", 50) == "Title-WithSpecialChars"

    # Test truncation
    long_title = "A" * 100
    result = sanitize_filename(long_title, 50)
    assert len(result) <= 50


def test_create_epub_for_story():
    """Test creating an EPUB file for a story."""
    story = {
        "id": 123,
        "title": "Test Story",
        "url": "http://test.com/story",
        "by": "testuser",
        "score": 100,
        "content": "<p>Story content here</p>",
    }

    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        output_path = f.name

    try:
        result = create_epub_for_story(story, output_path)
        assert result == output_path
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def test_main_function():
    """Test the main scraper function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_config = {
            "NUM_HN_STORIES": 2,
            "HN_API_BASE": "https://hacker-news.firebaseio.com/v0",
            "HN_FETCH_TIMEOUT": 10,
            "HN_MAX_FILENAME_LENGTH": 50,
            "TEXTS_DIR": tmpdir,
            "HACKERNEWS_SUBDIR": "hackernews",
            "SD_CARD_PATH": "/nonexistent",  # Won't try to copy
        }

        # Mock API responses
        mock_topstories = Mock()
        mock_topstories.json.return_value = [1, 2]
        mock_topstories.raise_for_status = Mock()

        mock_story = Mock()
        mock_story.json.return_value = {
            "id": 1,
            "title": "Test Story",
            "url": "http://test.com/story",
            "by": "testuser",
            "score": 100,
        }
        mock_story.raise_for_status = Mock()

        mock_article = Mock()
        mock_article.content = b"<html><body><p>Test article content</p></body></html>"
        mock_article.raise_for_status = Mock()

        with patch("bin.scrapers.scrape_hn_to_epub.get_config", return_value=mock_config):
            with patch("bin.scrapers.scrape_hn_to_epub.get_repo_root", return_value=tmpdir):
                with patch("bin.scrapers.scrape_hn_to_epub.requests.get") as mock_get:
                    mock_get.side_effect = [
                        mock_topstories,
                        mock_story,
                        mock_story,
                        mock_article,
                        mock_article,
                    ]

                    from bin.scrapers.scrape_hn_to_epub import main

                    # Should run without error
                    main()

                    # Check that EPUBs were created
                    hn_dir = os.path.join(tmpdir, "hackernews")
                    assert os.path.exists(hn_dir)
                    epubs = [f for f in os.listdir(hn_dir) if f.endswith(".epub")]
                    assert len(epubs) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
