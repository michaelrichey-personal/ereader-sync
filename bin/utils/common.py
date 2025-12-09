"""Common utility functions shared across e-reader scripts."""

import warnings


def suppress_urllib3_warning():
    """Suppress urllib3 LibreSSL warning on macOS."""
    warnings.filterwarnings("ignore", message=".*urllib3 v2 only supports OpenSSL.*")


def output_progress(successful, failures, processed, total, current_item):
    """Output standardized progress information for GUI/TUI parsing.

    Args:
        successful: Number of successfully processed items
        failures: Number of failed items
        processed: Total number of items processed so far
        total: Total number of items to process
        current_item: Description of the current item being processed

    Output Format:
        PROGRESS|successful|failures|processed|total|current_item

    Example:
        PROGRESS|5|1|6|10|Downloading article 7
    """
    print(f"PROGRESS|{successful}|{failures}|{processed}|{total}|{current_item}", flush=True)
