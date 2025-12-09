#!/usr/bin/env python3
"""Tests for the config_reader module."""
import os
import sys
import tempfile
from unittest.mock import patch
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bin.config_reader import get_repo_root, read_config_file, get_config


def test_get_repo_root():
    """Test that get_repo_root returns a valid directory."""
    repo_root = get_repo_root()
    assert os.path.exists(repo_root)
    assert os.path.isdir(repo_root)
    # Should contain the config directory
    assert os.path.exists(os.path.join(repo_root, "config"))


def test_read_config_file():
    """Test reading a config file with various data types."""
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".config", delete=False) as f:
        f.write("TEST_KEY=test_value\n")
        f.write("TEST_NUMBER=123\n")
        f.write("TEST_FLOAT=3.14\n")
        f.write("TEST_BOOL_TRUE=true\n")
        f.write("TEST_BOOL_FALSE=False\n")
        f.write("# Comment line\n")
        f.write("\n")  # Empty line
        temp_config = f.name

    try:
        # Test reading the config
        config = read_config_file(temp_config)
        assert config["TEST_KEY"] == "test_value"
        assert config["TEST_NUMBER"] == 123  # Should be converted to int
        assert config["TEST_FLOAT"] == 3.14  # Should be converted to float
        assert config["TEST_BOOL_TRUE"] is True  # Should be converted to bool
        assert config["TEST_BOOL_FALSE"] is False  # Should be converted to bool
    finally:
        os.remove(temp_config)


def test_read_config_file_missing():
    """Test that reading a missing config file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        read_config_file("/nonexistent/config/file")


def test_get_config_with_secrets():
    """Test get_config merges application and secrets config."""
    app_data = {"KEY1": "value1", "KEY2": 123}
    secrets_data = {"SECRET_KEY": "secret_value", "KEY2": 456}

    with patch("bin.config_reader.read_config_file") as mock_read:
        # First call returns app config, second returns secrets
        mock_read.side_effect = [app_data, secrets_data]

        config = get_config()

        # Should have both app and secrets, with secrets overriding
        assert config["KEY1"] == "value1"
        assert config["KEY2"] == 456  # Overridden by secrets
        assert config["SECRET_KEY"] == "secret_value"


def test_get_config_without_secrets():
    """Test get_config works when secrets.config is missing."""
    app_data = {"KEY1": "value1", "KEY2": 123}

    with patch("bin.config_reader.read_config_file") as mock_read:
        # First call returns app config, second raises FileNotFoundError
        mock_read.side_effect = [app_data, FileNotFoundError("secrets.config not found")]

        config = get_config()

        # Should have only app config
        assert config["KEY1"] == "value1"
        assert config["KEY2"] == 123
        assert "SECRET_KEY" not in config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
