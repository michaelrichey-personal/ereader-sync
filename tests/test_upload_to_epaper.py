#!/usr/bin/env python3
"""Tests for the upload_to_epaper module."""
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bin.upload_to_epaper import (
    find_ebook_files,
    create_folder,
    upload_file,
)


def test_find_ebook_files():
    """Test finding EPUB and XTC files in a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file structure
        os.makedirs(os.path.join(tmpdir, "subdir"))

        # Create test files
        epub_file = os.path.join(tmpdir, "test.epub")
        xtc_file = os.path.join(tmpdir, "test.xtc")
        txt_file = os.path.join(tmpdir, "test.txt")
        sub_epub = os.path.join(tmpdir, "subdir", "sub.epub")

        for f in [epub_file, xtc_file, txt_file, sub_epub]:
            open(f, "w").close()

        # Find ebook files
        files = find_ebook_files(tmpdir)

        # Should find 3 ebook files (.epub and .xtc)
        assert len(files) == 3
        assert any("test.epub" in f for f in files)
        assert any("test.xtc" in f for f in files)
        assert any("sub.epub" in f for f in files)
        assert not any("test.txt" in f for f in files)


def test_create_folder_success():
    """Test creating folder on device."""
    mock_response = Mock()
    mock_response.status_code = 200

    with patch("bin.upload_to_epaper.requests.put", return_value=mock_response) as mock_put:
        result = create_folder("test/folder", "http://192.168.1.100", 10)

        assert result is True
        mock_put.assert_called_once()


def test_create_folder_failure():
    """Test handling folder creation failure."""
    mock_response = Mock()
    mock_response.status_code = 500

    with patch("bin.upload_to_epaper.requests.put", return_value=mock_response):
        result = create_folder("test/folder", "http://192.168.1.100", 10)

        assert result is False


def test_upload_file_success():
    """Test successful file upload."""
    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        f.write(b"test content")
        test_file = f.name

    try:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        with patch("bin.upload_to_epaper.requests.post", return_value=mock_response) as mock_post:
            result = upload_file(
                test_file,
                "test.epub",
                "http://192.168.1.100/upload",
                10
            )

            assert result is True
            mock_post.assert_called_once()
    finally:
        os.remove(test_file)


def test_upload_file_failure():
    """Test handling upload failure."""
    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        f.write(b"test content")
        test_file = f.name

    try:
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Upload failed")

        with patch("bin.upload_to_epaper.requests.post", return_value=mock_response):
            result = upload_file(
                test_file,
                "test.epub",
                "http://192.168.1.100/upload",
                10
            )

            assert result is False
    finally:
        os.remove(test_file)


def test_upload_file_missing():
    """Test uploading a non-existent file."""
    result = upload_file(
        "/nonexistent/file.epub",
        "test.epub",
        "http://192.168.1.100/upload",
        10
    )

    assert result is False


def test_main_with_specific_files():
    """Test main function with specific files provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test EPUB file
        test_epub = os.path.join(tmpdir, "test.epub")
        with open(test_epub, "w") as f:
            f.write("test")

        mock_config = {
            "EPAPER_DEVICE_IP": "192.168.1.100",
            "EPAPER_UPLOAD_ENDPOINT": "/upload",
            "UPLOAD_TIMEOUT": 10,
            "UPLOAD_DELAY_SECONDS": 0,
            "TEXTS_DIR": tmpdir,
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        with patch("bin.upload_to_epaper.get_config", return_value=mock_config):
            with patch("bin.upload_to_epaper.get_repo_root", return_value=tmpdir):
                with patch("bin.upload_to_epaper.requests.post", return_value=mock_response):
                    with patch("sys.argv", ["upload_to_epaper.py", test_epub]):
                        from bin.upload_to_epaper import main

                        # Should not raise an exception
                        try:
                            main()
                        except SystemExit:
                            pass  # main() may call sys.exit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
