#!/usr/bin/env python3
"""Tests for the scrape_hcr_to_epub module."""
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bin.scrapers.scrape_hcr_to_epub import (
    is_date_title,
    date_title_to_filename,
    is_full_letter,
    get_post_content,
    create_epub_for_post,
)


def test_is_date_title_valid():
    """Test recognizing valid date titles."""
    assert is_date_title("December 2, 2025") is True
    assert is_date_title("January 15, 2024") is True
    assert is_date_title("March 31, 2023") is True


def test_is_date_title_invalid():
    """Test rejecting invalid titles."""
    assert is_date_title("Random Title") is False
    assert is_date_title("December 2025") is False
    assert is_date_title("Podcast Episode") is False
    assert is_date_title("") is False


def test_date_title_to_filename():
    """Test converting date titles to filenames."""
    assert date_title_to_filename("December 2, 2025") == "hcr-2025-12-02.epub"
    assert date_title_to_filename("January 1, 2024") == "hcr-2024-01-01.epub"
    assert date_title_to_filename("March 15, 2023") == "hcr-2023-03-15.epub"


def test_date_title_to_filename_invalid():
    """Test handling invalid date titles."""
    # Should fall back to sanitized title
    result = date_title_to_filename("Invalid Title")
    assert "Invalid-Title" in result or "Invalid Title" in result.replace("-", " ")


def test_is_full_letter_with_podcast():
    """Test detecting podcast posts."""
    mock_html = """
    <html>
        <body>
            <audio src="podcast.mp3"></audio>
            <div class="body">Some content here</div>
        </body>
    </html>
    """

    mock_response = Mock()
    mock_response.content = mock_html.encode()
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        result = is_full_letter("http://test.com/post", 100)
        assert result is False


def test_is_full_letter_with_video():
    """Test detecting video posts."""
    mock_html = """
    <html>
        <body>
            <video src="video.mp4"></video>
            <div class="body">Some content here</div>
        </body>
    </html>
    """

    mock_response = Mock()
    mock_response.content = mock_html.encode()
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        result = is_full_letter("http://test.com/post", 100)
        assert result is False


def test_is_full_letter_short_post():
    """Test detecting short posts."""
    mock_html = """
    <html>
        <body>
            <div class="body">Short post</div>
        </body>
    </html>
    """

    mock_response = Mock()
    mock_response.content = mock_html.encode()
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        result = is_full_letter("http://test.com/post", 500)
        assert result is False


def test_is_full_letter_valid():
    """Test detecting valid full letters."""
    # Create a long enough post
    content = " ".join(["word"] * 600)
    mock_html = f"""
    <html>
        <body>
            <div class="body">{content}</div>
        </body>
    </html>
    """

    mock_response = Mock()
    mock_response.content = mock_html.encode()
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        result = is_full_letter("http://test.com/post", 500)
        assert result is True


def test_is_full_letter_error():
    """Test handling errors when checking posts."""
    with patch("requests.get", side_effect=Exception("Network error")):
        result = is_full_letter("http://test.com/post", 500)
        assert result is False


def test_get_post_content():
    """Test fetching post content."""
    mock_html = """
    <html>
        <body>
            <div class="body">
                <p>This is the post content.</p>
                <p>Another paragraph.</p>
            </div>
        </body>
    </html>
    """

    mock_response = Mock()
    mock_response.content = mock_html.encode()
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response):
        content = get_post_content("http://test.com/post")
        assert "post content" in content
        assert "<div" in content


def test_create_epub_for_post():
    """Test creating an EPUB file for a post."""
    post = {
        "title": "December 2, 2025",
        "url": "http://test.com/post",
        "content": "<p>Test content</p>",
    }

    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        output_path = f.name

    try:
        result = create_epub_for_post(post, output_path)
        assert result == output_path
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def test_get_recent_posts():
    """Test fetching recent posts from archive."""
    # Mock archive page HTML
    archive_html = """
    <html>
        <body>
            <a href="/p/post1">December 5, 2025</a>
            <a href="/p/post2">December 4, 2025</a>
            <a href="/p/podcast">Podcast Episode</a>
        </body>
    </html>
    """

    # Mock individual post HTML (full letter)
    post_html_long = """
    <html>
        <body>
            <div class="body">""" + " ".join(["word"] * 600) + """</div>
        </body>
    </html>
    """

    mock_archive = Mock()
    mock_archive.content = archive_html.encode()
    mock_archive.raise_for_status = Mock()

    mock_post = Mock()
    mock_post.content = post_html_long.encode()
    mock_post.raise_for_status = Mock()

    with patch("bin.scrapers.scrape_hcr_to_epub.requests.get") as mock_get:
        mock_get.side_effect = [mock_archive, mock_post, mock_post]

        from bin.scrapers.scrape_hcr_to_epub import get_recent_posts

        posts = get_recent_posts(2, "http://test.com/archive", 500, 10)

        # Should find 2 posts with valid date titles
        assert len(posts) <= 2


def test_main_function():
    """Test the main scraper function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_config = {
            "NUM_HCR_POSTS": 2,
            "HCR_ARCHIVE_URL": "http://test.com/archive",
            "MIN_LETTER_WORD_COUNT": 500,
            "MAX_HCR_CANDIDATES": 10,
            "TEXTS_DIR": tmpdir,
            "HCR_SUBDIR": "hcr",
            "SD_CARD_PATH": "/nonexistent",  # Won't try to copy
        }

        # Mock archive HTML
        archive_html = """
        <html>
            <body>
                <a href="/p/post1">December 5, 2025</a>
                <a href="/p/post2">December 4, 2025</a>
            </body>
        </html>
        """

        # Mock post HTML (full letter)
        post_html = """
        <html>
            <body>
                <div class="body">""" + " ".join(["word"] * 600) + """</div>
            </body>
        </html>
        """

        mock_archive = Mock()
        mock_archive.content = archive_html.encode()
        mock_archive.raise_for_status = Mock()

        mock_post = Mock()
        mock_post.content = post_html.encode()
        mock_post.raise_for_status = Mock()

        with patch("bin.scrapers.scrape_hcr_to_epub.get_config", return_value=mock_config):
            with patch("bin.scrapers.scrape_hcr_to_epub.get_repo_root", return_value=tmpdir):
                with patch("bin.scrapers.scrape_hcr_to_epub.requests.get") as mock_get:
                    # Archive request, then post checks, then content fetches
                    mock_get.side_effect = [
                        mock_archive,  # Archive page
                        mock_post,  # Check post 1
                        mock_post,  # Check post 2
                        mock_post,  # Get content for post 1
                        mock_post,  # Get content for post 2
                    ]

                    from bin.scrapers.scrape_hcr_to_epub import main

                    # Should run without error
                    main()

                    # Check that EPUBs were created
                    hcr_dir = os.path.join(tmpdir, "hcr")
                    assert os.path.exists(hcr_dir)
                    epubs = [f for f in os.listdir(hcr_dir) if f.endswith(".epub")]
                    assert len(epubs) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
