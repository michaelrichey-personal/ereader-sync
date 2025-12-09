#!/usr/bin/env python3
"""
Tests for the XTC converter website (x4converter.rho.sh).

These tests verify that the external XTC converter service is still functioning
and that our conversion script can interact with it correctly.
"""

import os
import shutil
import sys
import tempfile
import time

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Configuration
XTC_CONVERTER_URL = "https://x4converter.rho.sh"
PAGE_LOAD_TIMEOUT = 30  # seconds
ELEMENT_WAIT_TIMEOUT = 15  # seconds
CONVERSION_TIMEOUT = 120  # seconds for full conversion test


def get_test_epub():
    """Find a test EPUB file from the texts directory."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    texts_dir = os.path.join(repo_root, "texts")

    # Look for any EPUB file
    for root, dirs, files in os.walk(texts_dir):
        for file in files:
            if file.lower().endswith(".epub"):
                return os.path.join(root, file)

    return None


def setup_chrome_driver(download_dir=None):
    """Set up Chrome driver with headless options."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    if download_dir:
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        chrome_options.add_experimental_option("prefs", prefs)

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        return driver
    except WebDriverException as e:
        pytest.skip(f"Chrome driver not available: {e}")


class TestXTCConverterWebsite:
    """Tests to verify the XTC converter website is functioning."""

    def test_website_loads(self):
        """Test that the XTC converter website loads successfully."""
        driver = setup_chrome_driver()
        try:
            driver.get(XTC_CONVERTER_URL)
            # Check that we got a page (not an error page)
            assert "x4converter" in driver.title.lower() or driver.find_elements(
                By.CSS_SELECTOR, 'input[type="file"]'
            ), "Website did not load correctly - title or file input not found"
        finally:
            driver.quit()

    def test_file_input_exists(self):
        """Test that the file input element exists on the page."""
        driver = setup_chrome_driver()
        try:
            driver.get(XTC_CONVERTER_URL)
            time.sleep(2)  # Wait for page to fully load

            # Try the specific ID first, then fall back to generic selector
            file_input = None
            try:
                file_input = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
                    EC.presence_of_element_located((By.ID, "fileInput"))
                )
            except TimeoutException:
                file_input = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
                )
            assert file_input is not None, "File input element not found"
        except TimeoutException:
            pytest.fail("File input element not found within timeout")
        finally:
            driver.quit()

    def test_export_button_exists(self):
        """Test that the Export to XTC button exists on the page."""
        driver = setup_chrome_driver()
        try:
            driver.get(XTC_CONVERTER_URL)
            time.sleep(2)

            # Look for export button - try ID first, then text
            export_button = None
            try:
                export_button = driver.find_element(By.ID, "exportBtn")
            except Exception:
                pass

            if not export_button:
                try:
                    export_button = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//button[contains(text(), 'Export')]")
                        )
                    )
                except TimeoutException:
                    pass

            assert export_button is not None, (
                "Export button not found. " "The website UI may have changed."
            )
        finally:
            driver.quit()

    def test_configuration_elements_exist(self):
        """Test that configuration elements (font, size, etc.) exist."""
        driver = setup_chrome_driver()
        try:
            driver.get(XTC_CONVERTER_URL)
            time.sleep(2)

            # Check for common configuration elements (updated for current website)
            expected_elements = {
                "fontFace": "Font face selector",
                "fontSize": "Font size slider",
                "fontSizeInput": "Font size input",
                "lineHeight": "Line height slider",
                "lineHeightInput": "Line height input",
                "qualityMode": "Quality mode selector (replaces bitDepth)",
                "orientation": "Orientation selector",
                "textAlign": "Text alignment selector",
                "margin": "Margin slider",
                "enableDithering": "Dithering checkbox",
                "enableNegative": "Negative/dark mode checkbox",
            }

            missing_elements = []
            for element_id, description in expected_elements.items():
                try:
                    element = driver.find_element(By.ID, element_id)
                    if element is None:
                        missing_elements.append(f"{element_id} ({description})")
                except Exception:
                    missing_elements.append(f"{element_id} ({description})")

            if missing_elements:
                pytest.fail(
                    f"Missing configuration elements: {', '.join(missing_elements)}. "
                    "The website UI may have changed."
                )
        finally:
            driver.quit()


class TestXTCConverterFunctionality:
    """Functional tests that perform actual conversions."""

    @pytest.mark.slow
    def test_epub_upload_and_convert(self):
        """Test uploading an EPUB file and converting to XTC.

        This is a full integration test that requires:
        - A test EPUB file in the texts/ directory
        - Chrome driver installed
        - Network access to x4converter.rho.sh
        """
        # Find a test EPUB
        test_epub = get_test_epub()
        if not test_epub:
            pytest.skip("No test EPUB file found in texts/ directory")

        # Create a copy so we don't modify the original
        with tempfile.TemporaryDirectory() as tmpdir:
            test_epub_copy = os.path.join(tmpdir, "test.epub")
            shutil.copy(test_epub, test_epub_copy)

            download_dir = os.path.join(tmpdir, "downloads")
            os.makedirs(download_dir)

            driver = setup_chrome_driver(download_dir)
            try:
                # Load the converter page
                driver.get(XTC_CONVERTER_URL)
                time.sleep(2)

                # Upload the EPUB file (try ID first, then fallback)
                try:
                    file_input = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
                        EC.presence_of_element_located((By.ID, "fileInput"))
                    )
                except TimeoutException:
                    file_input = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
                    )
                file_input.send_keys(test_epub_copy)

                # Wait for file to be processed - look for the book to load
                # The preview canvas should have content, or the book info should appear
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
                    # Take screenshot for debugging
                    pytest.fail("EPUB did not load within timeout - export button still disabled")

                # Click the export button (try ID first, then text)
                try:
                    export_button = driver.find_element(By.ID, "exportBtn")
                except Exception:
                    export_button = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//button[contains(text(), 'Export')]")
                        )
                    )

                # Scroll to button and click
                driver.execute_script("arguments[0].scrollIntoView(true);", export_button)
                time.sleep(1)

                driver.execute_script("arguments[0].click();", export_button)

                # Give conversion time to start
                time.sleep(2)

                # Wait for download to complete
                xtc_file = self._wait_for_download(download_dir, CONVERSION_TIMEOUT)

                assert xtc_file is not None, (
                    "XTC file was not downloaded within timeout. "
                    "The conversion may have failed or the website changed."
                )
                assert os.path.getsize(xtc_file) > 0, "Downloaded XTC file is empty"

            except TimeoutException as e:
                pytest.fail(f"Timeout during conversion: {e}")
            finally:
                driver.quit()

    def _wait_for_download(self, download_dir, timeout):
        """Wait for download to complete and return the XTC/XTG/XTH/XTCH file path."""
        seconds = 0
        while seconds < timeout:
            # Check for incomplete downloads
            crdownload_files = [f for f in os.listdir(download_dir) if f.endswith(".crdownload")]
            if not crdownload_files:
                # Check for completed files (XTC, XTG, XTH, or XTCH - format options)
                output_files = [
                    f for f in os.listdir(download_dir) if f.endswith((".xtc", ".xtg", ".xth", ".xtch"))
                ]
                if output_files:
                    return os.path.join(download_dir, output_files[0])
            time.sleep(1)
            seconds += 1
        return None


def run_quick_verification():
    """Run a quick verification that the website is accessible.

    This can be called directly without pytest for quick checks.
    Returns (success, message).
    """
    try:
        driver = setup_chrome_driver()
    except Exception as e:
        return False, f"Chrome driver not available: {e}"

    try:
        driver.get(XTC_CONVERTER_URL)
        time.sleep(2)

        # Check file input exists (try ID first, then fallback)
        try:
            try:
                WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
                    EC.presence_of_element_located((By.ID, "fileInput"))
                )
            except TimeoutException:
                WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
                )
        except TimeoutException:
            return False, "File input element not found - website may be down or changed"

        # Check export button exists (try ID first, then text)
        try:
            try:
                driver.find_element(By.ID, "exportBtn")
            except Exception:
                driver.find_element(
                    By.XPATH, "//button[contains(text(), 'Export')]"
                )
        except Exception:
            return False, "Export button not found - website UI may have changed"

        # Check configuration elements (updated for current website)
        missing = []
        for elem_id in ["fontFace", "fontSize", "orientation", "qualityMode"]:
            try:
                driver.find_element(By.ID, elem_id)
            except Exception:
                missing.append(elem_id)

        if missing:
            return False, f"Missing config elements: {missing} - website UI may have changed"

        return True, "XTC converter website is accessible and UI elements are present"

    except TimeoutException:
        return False, "Timeout loading website - may be down or slow"
    except Exception as e:
        return False, f"Error during verification: {e}"
    finally:
        driver.quit()


if __name__ == "__main__":
    # Run quick verification when executed directly
    print("=" * 60)
    print("XTC Converter Website Verification")
    print("=" * 60)

    success, message = run_quick_verification()

    if success:
        print(f"\n✓ SUCCESS: {message}")
        print("\nRunning full pytest suite...")
        pytest.main([__file__, "-v", "-m", "not slow"])
    else:
        print(f"\n✗ FAILED: {message}")
        sys.exit(1)
