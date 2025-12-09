#!/usr/bin/env python3
"""
Script to convert EPUB files to XTC format using x4converter.rho.sh.
Uses Selenium with headless Chrome to automate the web interface.
Replaces the original EPUB file with the resulting XTC file.

This tool uses x4converter.rho.sh created by Lukasz.
Support his work: https://buymeacoffee.com/ukasz

Usage:
    convert_epub_to_xtc.py file.epub              # Convert single file
    convert_epub_to_xtc.py file1.epub file2.epub  # Convert multiple files
    convert_epub_to_xtc.py --all                  # Convert all EPUBs in texts/
    convert_epub_to_xtc.py --keep-epub file.epub  # Keep EPUB after conversion
"""

import os
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import shutil

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from bin.config_reader import get_config, get_repo_root
from bin.utils.common import output_progress, suppress_urllib3_warning

# Suppress urllib3 warning
suppress_urllib3_warning()

# Thread-safe lock for progress reporting
progress_lock = threading.Lock()


def setup_chrome_driver(download_dir):
    """Set up Chrome driver with headless options and download directory."""
    chrome_options = Options()
    # Use new headless mode (more stable)
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    # Add user agent to avoid detection
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Set download directory
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Find chromedriver in PATH and use Service to explicitly specify it
    chromedriver_path = shutil.which("chromedriver")
    if not chromedriver_path:
        print("Error: chromedriver not found in PATH")
        print("\nPlease install chromedriver:")
        print("  macOS: brew install chromedriver")
        print("  Linux: apt-get install chromium-chromedriver")
        sys.exit(1)

    try:
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error: Could not create Chrome driver: {e}")
        print(f"  chromedriver path: {chromedriver_path}")
        print("\nPlease ensure Chrome/Chromium browser is also installed:")
        print("  macOS: brew install --cask google-chrome")
        print("  Linux: apt-get install chromium-browser")
        sys.exit(1)


def wait_for_download(download_dir, timeout=60):
    """Wait for download to complete (no .crdownload files)."""
    seconds = 0
    while seconds < timeout:
        # Check for any .crdownload files (Chrome incomplete downloads)
        crdownload_files = list(Path(download_dir).glob("*.crdownload"))
        if not crdownload_files:
            # Check if we have an output file
            # Formats: .xtc (legacy), .xtg (fast/1-bit), .xth (high quality), .xtch (high color)
            output_files = (
                list(Path(download_dir).glob("*.xtc"))
                + list(Path(download_dir).glob("*.xtg"))
                + list(Path(download_dir).glob("*.xth"))
                + list(Path(download_dir).glob("*.xtch"))
            )
            if output_files:
                return output_files[0]
        time.sleep(1)
        seconds += 1

    return None


def convert_epub_to_xtc(epub_path, config, keep_epub=False):
    """Convert a single EPUB file to XTC format.

    Args:
        epub_path: Path to the EPUB file to convert
        config: Configuration dictionary
        keep_epub: If True, don't delete the EPUB after conversion

    Returns:
        tuple: (success: bool, filename: str, error_msg: str or None)
    """
    epub_path = os.path.abspath(epub_path)
    filename = os.path.basename(epub_path)

    if not os.path.exists(epub_path):
        error_msg = f"File not found: {epub_path}"
        with progress_lock:
            print(f"Error: {error_msg}")
        return (False, filename, error_msg)

    if not epub_path.lower().endswith(".epub"):
        error_msg = f"Not an EPUB file: {epub_path}"
        with progress_lock:
            print(f"Error: {error_msg}")
        return (False, filename, error_msg)

    # Check if a converted file already exists (.xtc, .xtg, .xth, or .xtch)
    base_path = epub_path[:-5]  # Remove .epub extension
    for ext in [".xtc", ".xtg", ".xth", ".xtch"]:
        if os.path.exists(base_path + ext):
            with progress_lock:
                print(f"Skipping: {filename} (already converted to {ext})")
            # Delete the EPUB since conversion already exists
            if not keep_epub:
                try:
                    os.remove(epub_path)
                    with progress_lock:
                        print(f"  Removed: {filename}")
                except Exception as e:
                    with progress_lock:
                        print(f"  Warning: Could not remove {filename}: {e}")
            return (True, filename, "already_converted")

    # Create temporary download directory in system temp (Chrome sandboxing issue
    # prevents downloads to arbitrary directories on macOS)
    download_dir = tempfile.mkdtemp(prefix=f"xtc_{os.getpid()}_{threading.get_ident()}_")

    with progress_lock:
        print(f"Converting: {filename}")

    driver = None
    try:
        # Set up Chrome driver
        driver = setup_chrome_driver(download_dir)
        driver.set_window_size(1920, 1080)

        # Load x4converter.rho.sh
        with progress_lock:
            print(f"  [{filename}] Loading converter...", end=" ")
        driver.get("https://x4converter.rho.sh")
        time.sleep(2)
        with progress_lock:
            print("✓")

        # Find and click the file input
        with progress_lock:
            print(f"  [{filename}] Uploading EPUB...", end=" ")
        # Try ID first (current website), fallback to generic selector
        try:
            file_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "fileInput"))
            )
        except Exception:
            file_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
            )
        file_input.send_keys(epub_path)

        # Wait for EPUB to load and be processed
        # Check for book info to appear or export button to become enabled
        max_load_wait = 30
        book_loaded = False
        for _ in range(max_load_wait):
            time.sleep(1)
            # Check if book info appeared (indicates successful load)
            try:
                book_info = driver.find_element(By.ID, "bookInfo")
                if book_info and book_info.text.strip():
                    book_loaded = True
                    break
            except Exception:
                pass
            # Also check if export button became enabled
            try:
                export_btn = driver.find_element(By.ID, "exportBtn")
                if export_btn and not export_btn.get_attribute("disabled"):
                    book_loaded = True
                    break
            except Exception:
                pass

        if not book_loaded:
            error_msg = "EPUB did not load within timeout"
            with progress_lock:
                print(f"✗ {error_msg}")
            return (False, filename, error_msg)

        with progress_lock:
            print("✓")

        # Apply configuration settings
        with progress_lock:
            print(f"  [{filename}] Applying settings...", end=" ")

        # Font settings (fontFamily -> fontFace in new UI)
        if config.get("XTC_FONT_FAMILY"):
            try:
                font_select = driver.find_element(By.ID, "fontFace")
                font_select.send_keys(config["XTC_FONT_FAMILY"])
            except Exception:
                pass

        # Font size (now has both slider and input, use the input field)
        if config.get("XTC_FONT_SIZE"):
            try:
                font_size_input = driver.find_element(By.ID, "fontSizeInput")
                font_size_input.clear()
                font_size_input.send_keys(str(config["XTC_FONT_SIZE"]))
            except Exception:
                # Fallback to slider ID
                try:
                    font_size_input = driver.find_element(By.ID, "fontSize")
                    driver.execute_script(
                        f"arguments[0].value = {config['XTC_FONT_SIZE']}; "
                        "arguments[0].dispatchEvent(new Event('input'));",
                        font_size_input,
                    )
                except Exception:
                    pass

        # Line height (now has both slider and input, use the input field)
        if config.get("XTC_LINE_HEIGHT"):
            try:
                line_height_input = driver.find_element(By.ID, "lineHeightInput")
                line_height_input.clear()
                line_height_input.send_keys(str(config["XTC_LINE_HEIGHT"]))
            except Exception:
                # Fallback to slider ID
                try:
                    line_height_input = driver.find_element(By.ID, "lineHeight")
                    driver.execute_script(
                        f"arguments[0].value = {config['XTC_LINE_HEIGHT']}; "
                        "arguments[0].dispatchEvent(new Event('input'));",
                        line_height_input,
                    )
                except Exception:
                    pass

        # Quality mode (replaces bitDepth - "fast" for 1-bit XTG, "hq" for 2-bit XTH)
        if config.get("XTC_BIT_DEPTH"):
            try:
                quality_select = Select(driver.find_element(By.ID, "qualityMode"))
                # Map old bit depth values to new quality mode option values
                bit_depth = config["XTC_BIT_DEPTH"]
                if str(bit_depth) == "1":
                    quality_select.select_by_value("fast")
                else:
                    quality_select.select_by_value("hq")
            except Exception:
                pass

        # Orientation
        if config.get("XTC_ORIENTATION"):
            try:
                orientation_select = driver.find_element(By.ID, "orientation")
                orientation_select.send_keys(config["XTC_ORIENTATION"])
            except Exception:
                pass

        # Dithering
        if config.get("XTC_ENABLE_DITHERING") is not None:
            try:
                dither_checkbox = driver.find_element(By.ID, "enableDithering")
                if config["XTC_ENABLE_DITHERING"] != dither_checkbox.is_selected():
                    dither_checkbox.click()
            except Exception:
                pass

        # Negative/invert (dark mode)
        if config.get("XTC_ENABLE_NEGATIVE") is not None:
            try:
                negative_checkbox = driver.find_element(By.ID, "enableNegative")
                if config["XTC_ENABLE_NEGATIVE"] != negative_checkbox.is_selected():
                    negative_checkbox.click()
            except Exception:
                pass

        with progress_lock:
            print("✓")

        # Click "Export to XTC" button
        with progress_lock:
            print(f"  [{filename}] Starting conversion...", end=" ")
        try:
            # Try ID first (current website), then fallback to text search
            export_button = None
            try:
                export_button = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "exportBtn"))
                )
            except Exception:
                # Fallback to text-based search
                export_button = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//button[contains(text(), 'Export')]")
                    )
                )

            # Scroll to button
            driver.execute_script("arguments[0].scrollIntoView(true);", export_button)
            time.sleep(1)

            # Use JavaScript click (more reliable in headless mode)
            driver.execute_script("arguments[0].click();", export_button)
            with progress_lock:
                print("✓")
        except Exception as e:
            error_msg = f"Failed to click export button: {str(e)[:200]}"
            with progress_lock:
                print(f"✗ Error: {error_msg}")
            return (False, filename, error_msg)

        # Wait for download to complete
        with progress_lock:
            print(f"  [{filename}] Waiting for download...", end=" ")
        xtc_file = wait_for_download(
            download_dir, timeout=config.get("XTC_CONVERSION_TIMEOUT", 300)
        )

        if not xtc_file:
            error_msg = "Download timeout"
            with progress_lock:
                print(f"✗ {error_msg}")
            return (False, filename, error_msg)

        with progress_lock:
            print("✓")

        # Move output file to replace EPUB
        # Get the extension of the downloaded file (.xtc, .xtg, or .xth)
        output_ext = os.path.splitext(str(xtc_file))[1]
        with progress_lock:
            print(f"  [{filename}] Replacing EPUB with {output_ext.upper()[1:]}...", end=" ")
        output_target = epub_path[:-5] + output_ext  # Replace .epub with output extension

        # Remove old EPUB
        os.remove(epub_path)

        # Move output file to final location
        os.rename(str(xtc_file), output_target)

        with progress_lock:
            print("✓")
            print(f"  Success: {os.path.basename(output_target)}")

        return (True, filename, None)

    except Exception as e:
        error_msg = str(e)
        with progress_lock:
            print(f"✗ Error: {error_msg}")
        return (False, filename, error_msg)

    finally:
        if driver:
            driver.quit()

        # Clean up temp directory
        try:
            if os.path.exists(download_dir):
                for file in os.listdir(download_dir):
                    os.remove(os.path.join(download_dir, file))
                os.rmdir(download_dir)
        except Exception:
            pass


def find_epub_files(directory):
    """Recursively find all EPUB files in the directory."""
    epub_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".epub"):
                full_path = os.path.join(root, file)
                epub_files.append(full_path)
    return epub_files


def main():
    """Main function."""
    print("=" * 60)
    print("EPUB to XTC Converter")
    print("Powered by x4converter.rho.sh - Thanks to Lukasz!")
    print("Support his work: https://buymeacoffee.com/ukasz")
    print("=" * 60)

    # Load configuration
    config = get_config()
    repo_root = get_repo_root()

    # Parse arguments
    args = sys.argv[1:]
    keep_epub = False

    if "--keep-epub" in args:
        keep_epub = True
        args.remove("--keep-epub")

    # Determine which files to convert
    if len(args) < 1:
        print("\nUsage:")
        print("  convert_epub_to_xtc.py file.epub")
        print("  convert_epub_to_xtc.py file1.epub file2.epub")
        print("  convert_epub_to_xtc.py --all")
        print("  convert_epub_to_xtc.py --keep-epub file.epub  # Keep EPUB after conversion")
        sys.exit(1)

    epub_files = []

    if args[0] == "--all":
        # Find all EPUB files in texts directory
        texts_dir = os.path.join(repo_root, config["TEXTS_DIR"])
        print(f"\nSearching for EPUB files in: {texts_dir}")
        epub_files = find_epub_files(texts_dir)
    else:
        # Process specified files
        texts_dir = os.path.join(repo_root, config["TEXTS_DIR"])
        for arg in args:
            # Check if it's an absolute path
            if os.path.isabs(arg):
                file_path = arg
            else:
                # Try relative to texts_dir first
                file_path = os.path.join(texts_dir, arg)
                if not os.path.exists(file_path):
                    # Try relative to current directory
                    file_path = os.path.abspath(arg)

            if os.path.exists(file_path) and file_path.lower().endswith(".epub"):
                epub_files.append(file_path)
            else:
                print(f"Warning: File not found or not an EPUB: {arg}")

    if not epub_files:
        print("No EPUB files to convert!")
        return

    print(f"\nFound {len(epub_files)} EPUB file(s) to convert\n")

    # Convert files (in parallel if configured)
    print("=" * 60)
    print("Starting conversions")
    print("=" * 60 + "\n")

    success_count = 0
    fail_count = 0
    skipped_count = 0
    total_files = len(epub_files)
    completed = 0

    # Get max parallel conversions from config
    max_workers = config.get("XTC_MAX_PARALLEL_CONVERSIONS", 2)
    if max_workers < 1:
        max_workers = 1

    print(f"Using {max_workers} parallel conversion(s)")
    if keep_epub:
        print("EPUBs will be kept after conversion")
    print()

    # Output initial progress
    output_progress(0, 0, 0, total_files, "Starting EPUB to XTC conversion")

    # Use ThreadPoolExecutor for parallel conversions
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all conversions
        future_to_file = {
            executor.submit(convert_epub_to_xtc, file_path, config, keep_epub): file_path
            for file_path in epub_files
        }

        # Process results as they complete
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                success, filename, error_msg = future.result()
                completed += 1

                if success:
                    if error_msg == "already_converted":
                        skipped_count += 1
                        status_msg = f"Skipped: {filename}"
                    else:
                        success_count += 1
                        status_msg = f"Completed: {filename}"
                else:
                    fail_count += 1
                    status_msg = f"Failed: {filename}"

                # Update progress
                output_progress(
                    success_count + skipped_count,
                    fail_count,
                    completed,
                    total_files,
                    status_msg,
                )

            except Exception as e:
                fail_count += 1
                completed += 1
                with progress_lock:
                    print(f"Exception processing {os.path.basename(file_path)}: {e}")
                output_progress(
                    success_count,
                    fail_count,
                    completed,
                    total_files,
                    f"Error: {os.path.basename(file_path)}",
                )

            print()  # Blank line between files

    # Final progress
    output_progress(success_count + skipped_count, fail_count, completed, total_files, "Complete")

    # Summary
    print("=" * 60)
    print("Conversion Summary")
    print("=" * 60)
    print(f"Total files: {total_files}")
    print(f"Converted: {success_count}")
    print(f"Skipped (already converted): {skipped_count}")
    print(f"Failed: {fail_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
