# E-Reader Content Management System

A comprehensive system for scraping web content and syncing to an e-paper device.

## Quick Start

### 1. Install Dependencies

**Using uv (recommended - faster):**
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install core dependencies (TUI, scrapers, converters)
uv sync
```

**Optional: Add GUI Support**

The GUI uses CustomTkinter (modern, lightweight, zero dependency issues):

```bash
# Install GUI dependencies
uv sync --extra gui

# Or with pip:
pip3 install -e ".[gui]"
```

**⚠️  Important Notes:**
- **Tk 8.6 Required:** The GUI requires Python built with Tk 8.6 (NOT Tk 9.0). Tk 9.0 has a critical bug on macOS that breaks scrolling.
- **Python 3.12.12 Recommended:** Use Python 3.12.12 for best compatibility. Python 3.14+ includes Tk 9.0 by default.
- **Check your Tk version:** Run `python3 -c "import tkinter; print(tkinter.TclVersion)"` - it should output `8.6`
- If tkinter is missing or you have Tk 9.0, see `INSTALL.md` for setup instructions
- **Alternative:** The TUI (`ereader-tui`) has all the same features and requires no tkinter!

### 2. Configure

```bash
# Copy secrets template
cp config/secrets.config.template config/secrets.config

# Edit your WiFi passwords
vi config/secrets.config

# Optionally edit application settings
vi config/application.config
```

### 3. Run

**Graphical Interface:**
```bash
# If installed with uv pip install -e .
ereader-gui

# Or use the shell script
./ereader-gui
```

**Terminal Interface:**
```bash
# If installed with uv pip install -e .
ereader-tui

# Or use the shell script
./ereader-tui
```

**Command Line:**
```bash
# If installed with uv pip install -e ., you can use:
scrape-hcr          # Scrape HCR letters
scrape-hn           # Scrape Hacker News
convert-to-xtc      # Convert EPUB to XTC
upload-to-epaper    # Upload files to device

# Or run scripts directly:
python3 bin/scrape_hcr_to_epub.py
python3 bin/scrape_hn_to_epub.py
python3 bin/convert_epub_to_xtc.py
python3 bin/upload_to_epaper.py

# Sync to e-reader (with WiFi switching)
./bin/switch_to_epaper_wifi.sh
```

## Features

### Content Sources
- **Heather Cox Richardson**: Scrapes "Letters from an American" from Substack
- **Hacker News**: Scrapes top stories and their linked articles

### User Interfaces
- **GUI**: Kivy-based graphical interface with tabs for settings, secrets, generation, and sync
- **TUI**: Textual-based terminal interface with the same features
- **CLI**: Individual Python scripts for automation

### Configuration
All settings stored in `config/` directory:
- `application.config`: Network settings, device IPs, scraper options
- `secrets.config`: WiFi passwords (not committed to git)

### WiFi Management
Automatically switches to e-paper WiFi network, uploads files, and switches back to original network with safety features:
- 30-second timeout watchdog
- Emergency reconnect on errors
- Configurable timing values

## Troubleshooting

Having issues? See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for:
- WiFi switching problems
- Upload failures
- Configuration issues
- Step-by-step debugging guide

**Quick Tips:**
- Use "Test Upload (no WiFi switch)" button in GUI to isolate WiFi vs upload issues
- Run scripts from terminal to see detailed error messages
- Verify config files exist and have correct values

## Documentation

See [CLAUDE.md](CLAUDE.md) for detailed architecture and development information.

## File Structure

```
ereader/
├── bin/                    # Scripts
│   ├── config_reader.py    # Config utility
│   ├── gui.py             # Kivy GUI
│   ├── tui.py             # Textual TUI
│   ├── scrape_hcr_to_epub.py
│   ├── scrape_hn_to_epub.py
│   ├── upload_to_epaper.py
│   └── switch_to_epaper_wifi.sh
├── config/                # Configuration
│   ├── application.config
│   ├── secrets.config
│   └── secrets.config.template
├── texts/                 # Generated EPUBs
│   ├── hcr/              # HCR letters
│   └── hackernews/       # HN stories
├── ereader-gui           # GUI launcher
├── ereader-tui           # TUI launcher
└── requirements.txt      # Python dependencies
```

## License

This is personal software for managing e-reader content.
