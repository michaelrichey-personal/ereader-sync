#!/usr/bin/env python3
"""Tests for the common utilities module."""
import os
import sys
from io import StringIO
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bin.utils.common import output_progress, suppress_urllib3_warning


def test_output_progress():
    """Test that output_progress generates correct format."""
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        output_progress(5, 2, 7, 10, "Processing item 7")
        output = captured_output.getvalue()

        # Verify format: PROGRESS|successful|failures|processed|total|current_item
        assert output.startswith("PROGRESS|")
        parts = output.strip().split("|")
        assert len(parts) == 6
        assert parts[0] == "PROGRESS"
        assert parts[1] == "5"  # successful
        assert parts[2] == "2"  # failures
        assert parts[3] == "7"  # processed
        assert parts[4] == "10"  # total
        assert parts[5] == "Processing item 7"  # current_item
    finally:
        sys.stdout = old_stdout


def test_suppress_urllib3_warning():
    """Test that suppress_urllib3_warning doesn't raise exceptions."""
    # This should run without errors
    suppress_urllib3_warning()
    # Can't really test if warnings are suppressed without generating one,
    # but we can at least verify the function runs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
