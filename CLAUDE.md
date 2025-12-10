# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is an e-reader content management system that scrapes web content (Hacker News stories and Heather Cox Richardson's Substack letters) and converts them to EPUB format for reading on an e-paper device. The system includes automated WiFi network switching and file upload capabilities.

## Configuration

All configuration is stored in `config/` directory and are editable from the GUI and TUI:

- **application.config**: Non-sensitive settings (network names, device IP, directories, timing, scraper settings)
- **secrets.config**: Sensitive passwords (WiFi passwords) - **NOT committed to git**
- **secrets.config.template**: Template showing required secret values

**First-time setup:**
```bash
cp config/secrets.config.template config/secrets.config
# Edit secrets.config with your actual passwords
```

### Configurable Values

**Scraper Settings:**
- `NUM_HCR_POSTS` - Number of HCR letters to scrape (default: 5)
- `NUM_HN_STORIES` - Number of HN stories to scrape (default: 20)
- `MIN_LETTER_WORD_COUNT` - Minimum word count for valid HCR letters (default: 500)
- `MAX_HCR_CANDIDATES` - Maximum candidates to check when searching for HCR letters (default: 20)
- `HN_FETCH_TIMEOUT` - HTTP timeout in seconds when fetching HN articles (default: 10)
- `HN_MAX_FILENAME_LENGTH` - Maximum length for sanitized HN filenames (default: 50)

**Upload Settings:**
- `UPLOAD_TIMEOUT` - HTTP timeout in seconds for e-paper uploads (default: 30)
- `UPLOAD_DELAY_SECONDS` - Delay between consecutive uploads (default: 1)

**WiFi Settings:**
- `CONNECTION_WAIT_TIME` - Seconds to wait after connecting (default: 8)
- `MAX_RETRIES` - Maximum connection retry attempts (default: 3)
- `RETRY_DELAY` - Seconds between retry attempts (default: 5)

**XTC Conversion Settings:**
- `XTC_FONT_FAMILY` - Font family for XTC conversion
- `XTC_FONT_SIZE` - Font size for XTC conversion
- `XTC_LINE_HEIGHT` - Line height for XTC conversion
- `XTC_BIT_DEPTH` - Image bit depth (1, 4, or 8)
- `XTC_ORIENTATION` - Page orientation (portrait/landscape)
- `XTC_ENABLE_DITHERING` - Enable/disable dithering (true/false)
- `XTC_ENABLE_NEGATIVE` - Enable/disable negative mode (true/false)
- `XTC_CONVERSION_TIMEOUT` - Maximum seconds for conversion (default: 300)
- `XTC_MAX_PARALLEL_CONVERSIONS` - Number of files to convert simultaneously (default: 2)

## Architecture

The repository consists of scraper scripts, UI applications, orchestration scripts, and a configuration system:

### User Interfaces
- **gui.py**: CustomTkinter graphical interface with tabbed layout
  - Modern, lightweight GUI (no Kivy/pygame dependencies)
  - Settings tab for editing application.config
  - Secrets tab for editing secrets.config (password fields)
  - Generate tab with checkboxes to select HCR/HN scrapers
  - Convert tab for EPUB to XTC conversion
  - Sync tab with WiFi auto-switch option
  - All operations run in background threads
  - Requires Python with tkinter support

- **tui.py**: Textual-based terminal interface with same features as GUI
  - Keyboard-driven navigation
  - Real-time output logging
  - Notifications for save/reload operations
  - All operations run as async workers

### Configuration System
- **config_reader.py**: Python utility module for reading config files
  - `get_config()`: Returns merged application + secrets configuration as dict
  - `get_repo_root()`: Returns repository root directory path
  - Automatically converts numeric config values to integers
  - All Python scripts import and use this module

### Content Scrapers
- **scrape_hcr_to_epub.py**: Scrapes recent "Letters from an American" by Heather Cox Richardson from her Substack
  - Number of posts configured via `NUM_HCR_POSTS` (default: 5)
  - Filters for date-formatted titles (her daily letters) vs podcasts/videos
  - Validates posts are "full letters" (word count > `MIN_LETTER_WORD_COUNT`, default: 500)
  - Archive URL configured via `HCR_ARCHIVE_URL`
  - Creates individual EPUB files named `hcr-YYYY-MM-DD.epub`
  - Output directory: `TEXTS_DIR/HCR_SUBDIR` (default: `./texts/hcr/`)

- **scrape_hn_to_epub.py**: Scrapes top Hacker News stories with URLs
  - Number of stories configured via `NUM_HN_STORIES` (default: 20)
  - Uses HN Firebase API (base URL: `HN_API_BASE`)
  - Extracts article content via web scraping (handles various HTML structures)
  - Creates individual EPUBs numbered `01_title.epub`, `02_title.epub`, etc.
  - Output directory: `TEXTS_DIR/HACKERNEWS_SUBDIR` (default: `./texts/hackernews/`)

### Conversion System
- **convert_epub_to_xtc.py**: Converts EPUB files to XTC format for XTeink devices
  - Uses Selenium with headless Chrome to automate x4converter.rho.sh web interface
  - Supports single file, multiple files, or `--all` to convert entire directory
  - Applies configuration settings from `application.config` (font, size, orientation, etc.)
  - Replaces original EPUB with resulting XTC file
  - Outputs detailed progress including substeps (loading, uploading, converting, downloading)

### Upload System
- **upload_to_epaper.py**: Uploads EPUB and XTC files to the e-paper device
  - Recursively finds all `.epub` and `.xtc` files in `TEXTS_DIR` directory
  - Creates subdirectory structure on device matching local structure
  - POSTs files to `http://{EPAPER_DEVICE_IP}{EPAPER_UPLOAD_ENDPOINT}`
  - Device IP and endpoint configured in `application.config`
  - Uploads one file at a time with configurable delay between uploads
  - Supports selective upload by passing file paths as arguments

- **switch_to_epaper_wifi.sh**: Network orchestration wrapper
  - Sources both `application.config` and `secrets.config` at startup
  - Auto-detects current WiFi network and saves it
  - Switches to network specified by `EPAPER_NETWORK` config
  - Executes the upload script
  - Automatically switches back to original network (or `ORIGINAL_NETWORK_FALLBACK` if detection fails)
  - If already on E-Paper network, skips switch
  - All timing values configurable in `application.config`

## User Interfaces

The system provides three ways to interact:

### 1. Graphical User Interface (GUI)
```bash
./ereader-gui
# or
python3 bin/gui.py
```
CustomTkinter-based GUI with tabs for:
- **Settings**: Edit application configuration
- **Secrets**: Edit WiFi passwords (password-masked inputs)
- **Generate**: Scrape HCR/HN content with checkboxes
- **Convert**: Convert EPUB files to XTC format with file selection
- **Sync**: Upload to e-reader with optional WiFi switching

**Features:**
- Real-time progress bars and status updates for all operations
- Collapsible detail output view for verbose logging
- Auto-refresh file lists when switching to Convert/Sync tabs
- Progress tracking with success/failure counts
- Theme switcher (light/dark mode)

### 2. Terminal User Interface (TUI)
```bash
./ereader-tui
# or
python3 bin/tui.py
```
Textual-based TUI with the same features as GUI. Keyboard shortcuts:
- `q`: Quit
- Tab navigation between panes

**Features:**
- Real-time progress updates in log output
- Auto-refresh file lists when switching tabs
- Async workers for non-blocking operations
- Notifications for save/reload operations

### 3. Command Line Scripts
```bash
# Scrape HCR letters (creates 5 EPUBs in texts/)
python3 bin/scrape_hcr_to_epub.py

# Scrape Hacker News (creates 20 EPUBs in texts/hackernews/)
python3 bin/scrape_hn_to_epub.py

# Convert EPUB to XTC (single or multiple files)
python3 bin/convert_epub_to_xtc.py file.epub
python3 bin/convert_epub_to_xtc.py --all

# Upload to e-paper device
python3 bin/upload_to_epaper.py

# Full automated workflow: switch networks, upload, switch back
./bin/switch_to_epaper_wifi.sh

# Upload specific files
python3 bin/upload_to_epaper.py file1.epub file2.xtc
```

## Dependencies

Install all dependencies:
```bash
pip3 install -r requirements.txt
```

Required packages:
- **Scraping**: beautifulsoup4, requests, ebooklib, lxml
- **Conversion**: selenium (for EPUB to XTC via web automation)
- **TUI**: textual >= 0.48.0
- **GUI**: customtkinter >= 5.2.0 (requires tkinter - included with most Python installations)
- **Optional**: rich (enhanced terminal output)

**System Requirements:**
- Chrome or Chromium browser (for EPUB to XTC conversion)
- chromedriver (install via `brew install chromedriver` on macOS)

Legacy scraper-only requirements:
```bash
pip3 install -r bin/requirements_hcr_scraper.txt
```

## Real-Time Progress System

All scripts output standardized progress information for real-time UI updates in both GUI and TUI.

### Progress Output Format

Scripts output progress lines in the format (see `PROGRESS_FORMAT.md` for full specification):
```
PROGRESS|<successful>|<failures>|<processed>|<total>|<current_item>
```

Example:
```
PROGRESS|15|2|17|20|Uploading: hackernews/article.xtc
```

### How It Works

1. **Scripts Output Progress**: All processing scripts (scrapers, converter, uploader) output `PROGRESS|...` lines to stdout with `flush=True`
2. **GUI/TUI Parse Lines**: UIs read stdout line-by-line in real-time and parse PROGRESS lines
3. **UI Updates**:
   - Progress bars update to show `processed/total`
   - Status labels show current operation
   - Success/failure counts displayed

### Implementation Notes

- **Unbuffered Output**: Python scripts run with `-u` flag in bash wrapper for immediate output
- **Line Buffering**: Subprocess calls use `bufsize=1` for line-buffered reading
- **Non-Blocking**: GUI uses threads, TUI uses async workers
- **Backward Compatible**: Scripts still work from command line with readable output
- **Auto-Refresh**: Convert and Sync tabs auto-refresh file lists on tab switch and after operations complete

## Important Implementation Details

### Configuration Loading
- Python scripts use `config_reader.py` module to load config files
- Bash script sources config files directly (exports all variables)
- Config files use simple `KEY=value` format (no spaces around `=`)
- Numeric values automatically converted to integers in Python
- Missing `secrets.config` causes graceful warning in Python, hard error in bash

### HCR Scraper Specifics
- Only scrapes posts with date-formatted titles matching: `Month DD, YYYY`
- Checks up to `MAX_HCR_CANDIDATES` posts to find `NUM_HCR_POSTS` valid letters
- Validates content length (>`MIN_LETTER_WORD_COUNT`) to filter out short posts
- Checks for and excludes podcast/video posts (looks for `<audio>`, `<video>` tags)
- Can auto-copy to SD card at `SD_CARD_PATH` if mounted

### Hacker News Scraper Specifics
- Skips "Ask HN" posts (no external URL)
- Uses `HN_FETCH_TIMEOUT` second timeout for article fetching
- Truncates filenames to `HN_MAX_FILENAME_LENGTH` characters
- Uses multiple fallback selectors to extract article content
- Preserves basic HTML structure (headings, paragraphs, lists, blockquotes)
- Includes HN metadata: score, author, discussion link

### EPUB to XTC Converter Specifics
- Uses headless Chrome with Selenium for web automation
- Automates x4converter.rho.sh web interface
- Waits for file upload, processing, and download completion
- Applies all configuration settings from `application.config`
- Creates temporary download directory for each conversion
- Removes original EPUB and replaces with XTC file
- Handles conversion timeouts (configurable via `XTC_CONVERSION_TIMEOUT`)
- Supports parallel conversions (configurable via `XTC_MAX_PARALLEL_CONVERSIONS`, default: 2)
- Uses ThreadPoolExecutor for thread-safe parallel processing
- Outputs progress for GUI/TUI tracking with thread-safe locking

### WiFi Switching Safety
- Uses macOS `networksetup` commands for WiFi interface specified in `WIFI_INTERFACE`
- Falls back to `ORIGINAL_NETWORK_FALLBACK` network if auto-detection fails
- All timing values configurable: `CONNECTION_WAIT_TIME`, `MAX_RETRIES`, `RETRY_DELAY`
- Runs Python with `-u` flag for unbuffered output to enable real-time progress in GUI/TUI

### E-Paper Device
- Device IP and endpoint configured via `EPAPER_DEVICE_IP` and `EPAPER_UPLOAD_ENDPOINT`
- Upload timeout: `UPLOAD_TIMEOUT` seconds (default: 30)
- Delay between uploads: `UPLOAD_DELAY_SECONDS` seconds (default: 1)
- Expects multipart form data with field name `data`
- Files uploaded to device root: `/{filename}`

## Output Locations

All scripts use paths from configuration:
- HCR letters: `{TEXTS_DIR}/{HCR_SUBDIR}/hcr-YYYY-MM-DD.epub` (default: `./texts/hcr/`)
- HN stories: `{TEXTS_DIR}/{HACKERNEWS_SUBDIR}/title.epub` (default: `./texts/hackernews/`)
- XTC files: Conversion replaces `.epub` with `.xtc` in same directory
- SD card (optional): `{SD_CARD_PATH}` (default: `/Volumes/NO NAME/`)
  - HCR copies to: `{SD_CARD_PATH}/{HCR_SUBDIR}/`
  - HN copies to: `{SD_CARD_PATH}/{HACKERNEWS_SUBDIR}/`

## Modifying Configuration

Three ways to modify configuration:

1. **Via GUI/TUI**: Use the Settings and Secrets tabs to edit values visually
2. **Via Text Editor**: Directly edit config files
   - Network names, IPs, directories → `config/application.config`
   - WiFi passwords → `config/secrets.config`
3. No code changes required - configuration is loaded at runtime

## Development Notes

### Code Organization
- Every script is in ./bin
  - Every scraper is in ./bin/scrapers
  - Every converter is in ./bin/converters
  - All common code is in ./bin/utils
- Every test is in ./tests

### GUI Implementation
- Uses CustomTkinter framework for modern, native-looking GUI
- Background threads prevent UI blocking during long operations
- Real-time subprocess output streaming with line-by-line parsing
- Progress bars and status labels update live during operations
- Config saved with proper categorization and comments
- Tab switching triggers automatic file list refresh
- Quit button in bottom right corner for easy application exit

### TUI Implementation
- Uses Textual framework for rich terminal interface
- Async workers for non-blocking operations
- Real-time log output using Log widget
- Custom CSS styling for consistent appearance

### Known Issues and Solutions

#### Tk 9.0 MouseWheel Bug on macOS (RESOLVED)
**Issue:** MouseWheel events are not captured on macOS with Tk 9.0, preventing trackpad/mouse wheel scrolling in the GUI.

**Root Cause:** Tk 9.0 introduced breaking changes to mousewheel event handling (TIP 474) that broke macOS trackpad scrolling. This is a Tk 9.0 regression, not a CustomTkinter or application code issue.

**Solution:** Use Python 3.12.12 built with Tk 8.6 instead of Tk 9.0:
```bash
# Install Tk 8.6
brew install tcl-tk@8

# Link Tk 8.6 (temporarily)
brew unlink tcl-tk && brew link tcl-tk@8 --force

# Install Python 3.12.12 with Tk 8.6
pyenv install 3.12.12

# Recreate virtualenv
pyenv virtualenv-delete -f ereaderenv
pyenv virtualenv 3.12.12 ereaderenv

# Relink Tk 9.0 if needed for other projects
# brew unlink tcl-tk@8 && brew link tcl-tk
```

**Verification:** Scrolling now works properly with trackpad and mouse wheel in all GUI tabs.

**Changes Made:**
- Converted `SecretsTab` from `CTkScrollableFrame` to `CTkFrame` (no scrollbar needed for 2-3 fields)
- Removed unnecessary master reassignment hacks from both tabs
- Existing mousewheel scrolling code works correctly with Tk 8.6

**References:**
- [TIP 474: Treat mouse wheel events in a uniform way](https://core.tcl-lang.org/tips/doc/trunk/tip/474.md)
- [Python Issue #127359: macOS CI failing due to Tk 9](https://github.com/python/cpython/issues/127359)
- [Homebrew Tk 9.0 upgrade issues](https://github.com/pyenv/pyenv/issues/3116)

### General Developer notes
- follow the directory layout when possible all tests go in bin/tests
- test all code changes
- run black, pylint, and ruff over code regularly
- update comments and documentation
- don't use magic numbers, allow the users to configure any values in configuration files and surface those configurations to the gui and tui
