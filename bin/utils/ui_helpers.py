"""
Shared UI helper functions for both GUI and TUI.

This module contains common code that was previously duplicated between
bin/gui.py and bin/tui.py, following the DRY (Don't Repeat Yourself) principle.
"""

import os
import re

from bin.config_reader import get_repo_root, read_config_file

# Core (non-scraper) configuration categories
CORE_CONFIG_CATEGORIES = {
    "WiFi Network Settings": [
        "EPAPER_NETWORK",
        "WIFI_INTERFACE",
        "ORIGINAL_NETWORK_FALLBACK",
    ],
    "Network Timing Configuration (seconds)": [
        "CONNECTION_WAIT_TIME",
        "MAX_RETRIES",
        "RETRY_DELAY",
        "EPAPER_TIMEOUT",
    ],
    "E-Paper Device Settings": ["EPAPER_DEVICE_IP", "EPAPER_UPLOAD_ENDPOINT"],
    "Directory Configuration": [
        "TEXTS_DIR",
        "SD_CARD_PATH",
    ],
    "Upload Configuration": ["UPLOAD_TIMEOUT", "UPLOAD_DELAY_SECONDS"],
    "XTC Conversion Configuration": [
        "XTC_FONT_FAMILY",
        "XTC_FONT_SIZE",
        "XTC_LINE_HEIGHT",
        "XTC_BIT_DEPTH",
        "XTC_ORIENTATION",
        "XTC_ENABLE_DITHERING",
        "XTC_ENABLE_NEGATIVE",
        "XTC_CONVERSION_TIMEOUT",
        "XTC_MAX_PARALLEL_CONVERSIONS",
    ],
    "GUI Configuration": ["GUI_SHOW_RAW_OUTPUT", "GUI_THEME"],
}

# Known scraper prefixes and their display names
KNOWN_SCRAPER_PREFIXES = {
    "HCR": "HCR (Letters from an American)",
    "HN": "Hacker News",
    "HACKERNEWS": "Hacker News",
    "HACKADAY": "Hackaday",
}

# Special case keys that belong to scrapers but don't follow standard naming
SCRAPER_SPECIAL_KEYS = {
    "MIN_LETTER_WORD_COUNT": "HCR",
    "MAX_HCR_CANDIDATES": "HCR",
    "HACKERNEWS_SUBDIR": "HN",
}


def detect_scraper_prefix(key):
    """Detect if a config key belongs to a scraper and return the prefix.

    Args:
        key: Configuration key name

    Returns:
        Tuple of (prefix, display_name) or (None, None) if not a scraper setting
    """
    # Check special case keys first
    if key in SCRAPER_SPECIAL_KEYS:
        prefix = SCRAPER_SPECIAL_KEYS[key]
        return prefix, KNOWN_SCRAPER_PREFIXES.get(prefix, prefix)

    # Check known prefixes
    for prefix, display_name in KNOWN_SCRAPER_PREFIXES.items():
        if key.startswith(f"{prefix}_") or key.startswith(f"NUM_{prefix}_"):
            return prefix, display_name

    # Auto-detect pattern: KEY_SUBDIR suggests a scraper output directory
    if key.endswith("_SUBDIR") and key not in ["HCR_SUBDIR", "HACKERNEWS_SUBDIR"]:
        prefix = key[:-7]  # Remove _SUBDIR
        display_name = prefix.replace("_", " ").title()
        return prefix, display_name

    # Auto-detect pattern: NUM_XXX_ITEMS or NUM_XXX_STORIES or NUM_XXX_POSTS or NUM_XXX_ARTICLES
    match = re.match(r"NUM_([A-Z_]+)_(ITEMS|STORIES|POSTS|ARTICLES)", key)
    if match:
        prefix = match.group(1)
        display_name = prefix.replace("_", " ").title()
        return prefix, display_name

    # Auto-detect pattern: XXX_FETCH_TIMEOUT, XXX_API_BASE, XXX_BLOG_URL, etc.
    scraper_suffixes = [
        "_FETCH_TIMEOUT",
        "_API_BASE",
        "_BLOG_URL",
        "_ARCHIVE_URL",
        "_MAX_FILENAME_LENGTH",
        "_SUBDIR",
    ]
    for suffix in scraper_suffixes:
        if key.endswith(suffix):
            prefix = key[: -len(suffix)]
            if prefix and prefix not in ["UPLOAD", "XTC", "EPAPER", "CONNECTION"]:
                display_name = KNOWN_SCRAPER_PREFIXES.get(prefix, prefix.replace("_", " ").title())
                return prefix, display_name

    return None, None


def get_scraper_categories(config):
    """Auto-detect scraper settings from config and group them by scraper.

    Args:
        config: Dict of configuration key -> value pairs

    Returns:
        Dict of category_name -> list of keys, ordered by category name
    """
    scraper_settings = {}  # prefix -> list of keys

    for key in config.keys():
        prefix, display_name = detect_scraper_prefix(key)
        if prefix:
            if prefix not in scraper_settings:
                scraper_settings[prefix] = {"display_name": display_name, "keys": []}
            scraper_settings[prefix]["keys"].append(key)

    # Convert to ordered categories dict
    categories = {}
    for prefix in sorted(scraper_settings.keys()):
        info = scraper_settings[prefix]
        category_name = f"{info['display_name']} Scraper"
        # Sort keys within each category for consistent ordering
        categories[category_name] = sorted(info["keys"])

    return categories


def get_all_config_categories(config=None):
    """Get all configuration categories, including auto-detected scraper settings.

    Args:
        config: Optional dict of configuration. If None, reads from file.

    Returns:
        Tuple of (core_categories, scraper_categories)
        - core_categories: Dict of non-scraper settings
        - scraper_categories: Dict of auto-detected scraper settings
    """
    if config is None:
        config = read_config_file("application.config")

    scraper_categories = get_scraper_categories(config)

    return CORE_CONFIG_CATEGORIES, scraper_categories


def get_uncategorized_settings(config):
    """Find settings that aren't in any known category.

    Args:
        config: Dict of configuration key -> value pairs

    Returns:
        List of uncategorized keys
    """
    # Collect all categorized keys
    categorized = set()

    # Add core category keys
    for keys in CORE_CONFIG_CATEGORIES.values():
        categorized.update(keys)

    # Add scraper category keys
    scraper_categories = get_scraper_categories(config)
    for keys in scraper_categories.values():
        categorized.update(keys)

    # Find uncategorized
    uncategorized = [key for key in config.keys() if key not in categorized]
    return sorted(uncategorized)


# Legacy: CONFIG_CATEGORIES for backward compatibility
# This combines core + known scraper settings
CONFIG_CATEGORIES = {
    **CORE_CONFIG_CATEGORIES,
    "HCR Scraper": [
        "HCR_ARCHIVE_URL",
        "NUM_HCR_POSTS",
        "MIN_LETTER_WORD_COUNT",
        "MAX_HCR_CANDIDATES",
        "HCR_SUBDIR",
    ],
    "Hacker News Scraper": [
        "HN_API_BASE",
        "NUM_HN_STORIES",
        "HN_FETCH_TIMEOUT",
        "HN_MAX_FILENAME_LENGTH",
        "HACKERNEWS_SUBDIR",
    ],
}


def parse_progress_line(line):
    """Parse a PROGRESS line and return parsed data or None.

    Args:
        line: String line to parse

    Returns:
        Tuple of (successful, failures, processed, total, current_item) or None if not a progress line

    Example:
        >>> parse_progress_line("PROGRESS|5|1|6|10|Downloading article 7")
        (5, 1, 6, 10, "Downloading article 7")
    """
    if line.startswith("PROGRESS|"):
        try:
            parts = line[9:].split("|", 4)  # Skip "PROGRESS|" prefix
            if len(parts) == 5:
                successful = int(parts[0])
                failures = int(parts[1])
                processed = int(parts[2])
                total = int(parts[3])
                current_item = parts[4].strip()
                return (successful, failures, processed, total, current_item)
        except (ValueError, IndexError):
            pass
    return None


def discover_scrapers():
    """Discover available scrapers from bin/scrapers directory.

    Returns:
        List of tuples: (display_name, script_path, source_name)
        Sorted by display_name

    Example:
        [("HCR", "/path/to/scrape_hcr_to_epub.py", "hcr"),
         ("Hacker News", "/path/to/scrape_hn_to_epub.py", "hn")]
    """
    repo_root = get_repo_root()
    scrapers_dir = os.path.join(repo_root, "bin", "scrapers")
    discovered = []

    if not os.path.exists(scrapers_dir):
        return discovered

    # Find all scrape_*_to_epub.py files
    for file in os.listdir(scrapers_dir):
        if file.startswith("scrape_") and file.endswith("_to_epub.py"):
            # Extract source name from filename
            source_name = file[7:-11]  # Remove 'scrape_' and '_to_epub.py'
            display_name = (
                source_name.upper()
                if len(source_name) <= 3
                else source_name.replace("_", " ").title()
            )

            script_path = os.path.join(scrapers_dir, file)
            discovered.append((display_name, script_path, source_name))

    # Sort by display name
    discovered.sort(key=lambda x: x[0])
    return discovered


def load_epub_files(file_extension=None):
    """Load list of EPUB and/or XTC files from texts directory.

    Args:
        file_extension: Filter by extension (".epub", ".xtc", or None for all ebooks)

    Returns:
        Tuple of (files, error_message)
        - files: List of tuples (rel_path, full_path, size_kb)
        - error_message: String error message or None if successful

    Example:
        >>> files, error = load_epub_files(".epub")
        >>> if not error:
        ...     for rel_path, full_path, size_kb in files:
        ...         print(f"{rel_path}: {size_kb:.1f} KB")
    """
    try:
        repo_root = get_repo_root()
        config = read_config_file("application.config")
        texts_dir = os.path.join(repo_root, config["TEXTS_DIR"])

        if not os.path.exists(texts_dir):
            return [], f"Error: Directory not found: {texts_dir}"

        # Determine which extensions to include
        # XTC formats: .xtc (legacy), .xtg (fast), .xth (high quality), .xtch (high color)
        if file_extension:
            extensions = [file_extension.lower()]
        else:
            extensions = [".epub", ".xtc", ".xtg", ".xth", ".xtch"]

        # Find all matching files
        ebook_files = []
        for root, dirs, files in os.walk(texts_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in extensions):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, texts_dir)
                    size = os.path.getsize(full_path)
                    size_kb = size / 1024
                    ebook_files.append((rel_path, full_path, size_kb))

        ebook_files.sort()
        return ebook_files, None

    except Exception as e:
        return [], f"Error loading files: {e}"


def save_application_config(config_values):
    """Save application configuration to file.

    Args:
        config_values: Dict of config key -> value pairs

    Returns:
        Tuple of (success: bool, message: str)

    Example:
        >>> config = {"EPAPER_NETWORK": "MyNetwork", "NUM_HN_STORIES": "20"}
        >>> success, msg = save_application_config(config)
        >>> if success:
        ...     print(msg)  # "Configuration saved successfully!"
    """
    try:
        repo_root = get_repo_root()
        config_path = os.path.join(repo_root, "config", "application.config")

        # Get categories dynamically
        core_categories, scraper_categories = get_all_config_categories(config_values)

        # Track which keys we've written
        written_keys = set()

        with open(config_path, "w") as f:
            f.write("# application.config\n")
            f.write("# Application configuration settings\n")
            f.write(
                "# All numeric values are in their respective units (seconds, counts, etc.)\n\n"
            )

            # Write core settings first
            for category, keys in core_categories.items():
                f.write(f"# {category}\n")
                for key in keys:
                    if key in config_values:
                        value = config_values[key]
                        f.write(f"{key}={value}\n")
                        written_keys.add(key)
                f.write("\n")

            # Write scraper settings
            for category, keys in scraper_categories.items():
                f.write(f"# {category}\n")
                for key in keys:
                    if key in config_values:
                        value = config_values[key]
                        f.write(f"{key}={value}\n")
                        written_keys.add(key)
                f.write("\n")

            # Write any uncategorized settings
            uncategorized = [k for k in config_values.keys() if k not in written_keys]
            if uncategorized:
                f.write("# Other Settings\n")
                for key in sorted(uncategorized):
                    value = config_values[key]
                    f.write(f"{key}={value}\n")
                f.write("\n")

        return True, "Configuration saved successfully!"
    except Exception as e:
        return False, f"Error saving config: {e}"


def save_secrets_config(secrets_values):
    """Save secrets configuration to file.

    Args:
        secrets_values: Dict of secret key -> value pairs

    Returns:
        Tuple of (success: bool, message: str)

    Example:
        >>> secrets = {"EPAPER_NETWORK_PASSWORD": "mypassword"}
        >>> success, msg = save_secrets_config(secrets)
        >>> if success:
        ...     print(msg)  # "Secrets saved successfully!"
    """
    try:
        repo_root = get_repo_root()
        config_path = os.path.join(repo_root, "config", "secrets.config")

        with open(config_path, "w") as f:
            f.write("# secrets.config\n")
            f.write(
                "# WARNING: This file contains sensitive information. Do not commit to version control!\n\n"
            )
            f.write("# WiFi Network Passwords\n")

            for key, value in sorted(secrets_values.items()):
                f.write(f"{key}={value}\n")

        return True, "Secrets saved successfully!"
    except Exception as e:
        return False, f"Error saving secrets: {e}"
