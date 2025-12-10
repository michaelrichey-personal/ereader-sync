# E-Reader Content Management System

A comprehensive system for scraping web content, converting to EPUB/XTC format, and syncing to an e-paper device.

## Features

- **Content Scrapers**: Fetch top Hacker News stories, Hackaday Blog, and HCR's "Letters from an American"
- **Format Conversion**: Convert EPUB files to XTC format for XTEink devices
- **WiFi Management**: Automatically switch networks to upload to e-paper device
- **Multiple Interfaces**: GUI, TUI, and CLI options
- **Configurable**: All settings in simple config files

## Requirements

- **Python**: 3.9 - 3.13 (3.12.12 recommended)
- **macOS or Linux** (WiFi switching only works on macOS)
- **Chrome/Chromium** + ChromeDriver (for EPUB to XTC conversion)

## Quick Install

```bash
git clone git@github.com/michaelrichey-personal/ereader-sync.git
cd ereader-sync
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync                # Install dependencies (use 'uv sync --extra gui' for GUI)
cp config/secrets.config.template config/secrets.config
# Edit config/secrets.config with your WiFi passwords
uv run ereader-tui     # Run the terminal interface
```

Don't have uv? Install it: `curl -LsSf https://astral.sh/uv/install.sh | sh`

**For EPUB to XTC conversion**, install ChromeDriver: `brew install chromedriver` (macOS) or `sudo apt-get install chromium-chromedriver` (Debian/Ubuntu)

## Detailed Installation

### 1. Clone the Repository

```bash
git clone https://github.com/michaelrichey-personal/ereader-sync.git
cd ereader-sync
```

### 2. Install Dependencies

**Using uv (Recommended):**
```bash
uv sync                  # TUI + scrapers + converter
uv sync --extra gui      # Add GUI support
uv sync --extra dev      # Add development tools
```

**Using pip:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install customtkinter>=5.2.0  # Optional: for GUI
```

### 3. Configure

```bash
cp config/secrets.config.template config/secrets.config
nano config/secrets.config  # Add your WiFi passwords
```

Optionally edit `config/application.config` to customize scraper settings, device IP, etc.

### 4. Install ChromeDriver (for EPUB to XTC conversion)

```bash
brew install chromedriver        # macOS
sudo apt-get install chromium-chromedriver  # Debian/Ubuntu
```

### 5. Run

**GUI (Graphical Interface):**
```bash
uv run ereader-gui
# or: source .venv/bin/activate && ./ereader-gui
```

**TUI (Terminal Interface):**
```bash
uv run ereader-tui
# or: source .venv/bin/activate && ./ereader-tui
```

**CLI (Command Line):**
```bash
# Scrape content
uv run scrape-hcr       # Heather Cox Richardson letters
uv run scrape-hn        # Hacker News top stories

# Convert EPUB to XTC
uv run convert-to-xtc --all

# Upload to e-reader (with WiFi switching)
./bin/switch_to_epaper_wifi.sh

# Upload without WiFi switching (if already on e-paper network)
uv run upload-to-epaper
```

## Documentation

- **[INSTALL.md](INSTALL.md)** - Detailed installation guide with troubleshooting
- **[CLAUDE.md](CLAUDE.md)** - Architecture and development documentation
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions

## Project Structure

```
ereader-sync/
├── bin/                      # All scripts
│   ├── gui.py               # CustomTkinter GUI
│   ├── tui.py               # Textual TUI
│   ├── scrape_hcr_to_epub.py
│   ├── scrape_hackaday_to_epub.py
│   ├── scrape_hn_to_epub.py
│   ├── convert_epub_to_xtc.py
│   ├── upload_to_epaper.py
│   ├── switch_to_epaper_wifi.sh
│   └── utils/               # Shared utilities
│       └── config_reader.py
├── config/                   # Configuration files
│   ├── application.config   # App settings (committed)
│   ├── secrets.config       # Passwords (NOT committed)
│   └── secrets.config.template
├── texts/                    # Generated content
│   ├── hcr/                 # HCR letters
│   ├── hackaday/            # Hackaday blog
│   └── hackernews/          # HN stories
├── tests/                    # Test files
├── ereader-gui              # GUI launcher script
├── ereader-tui              # TUI launcher script
├── requirements.txt
└── pyproject.toml
```

## Configuration

All configuration is in the `config/` directory:

| File | Purpose | Git Status |
|------|---------|------------|
| `application.config` | Network names, device IP, scraper settings | Committed |
| `secrets.config` | WiFi passwords | **NOT committed** |
| `secrets.config.template` | Template for secrets | Committed |

### Key Settings

**Scraper Settings:**
- `NUM_HCR_POSTS` - Number of HCR letters to fetch (default: 5)
- `NUM_HN_STORIES` - Number of HN stories to fetch (default: 20)
- `NUM_HACKADAY_ARTICLES` - Number of Hackaday articles to fetch (default: 10)

**Device Settings:**
- `EPAPER_DEVICE_IP` - IP address of your e-paper device
- `EPAPER_NETWORK` - WiFi network name for e-paper device

**Conversion Settings:**
- `XTC_FONT_FAMILY`, `XTC_FONT_SIZE` - Font settings
- `XTC_ORIENTATION` - portrait or landscape

See `config/application.config` for all available options.

## Troubleshooting

### GUI won't start / Scrolling doesn't work

The GUI requires Python built with **Tk 8.6** (not Tk 9.0). Tk 9.0 has a bug that breaks scrolling on macOS.

Check your Tk version:
```bash
python3 -c "import tkinter; print(tkinter.TclVersion)"
# Should output: 8.6
```

If you have Tk 9.0, see [INSTALL.md](INSTALL.md) for instructions on installing Python with Tk 8.6.

**Alternative:** The TUI (`./ereader-tui`) has all the same features and doesn't require tkinter!

### ChromeDriver errors

Make sure ChromeDriver is installed and matches your Chrome version:
```bash
chromedriver --version
```

### WiFi switching fails

WiFi switching only works on macOS and requires the correct network names in your config files.

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more solutions.

## License

MIT License - See LICENSE file for details.
