# Installation Guide

Complete installation instructions for the E-Reader Content Management System.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Install](#quick-install)
- [Detailed Installation](#detailed-installation)
- [Platform-Specific Instructions](#platform-specific-instructions)
- [GUI Setup (Tk 8.6 Requirement)](#gui-setup-tk-86-requirement)
- [Verifying Installation](#verifying-installation)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.9 - 3.13 | 3.12.12 recommended |
| Git | Any recent | For cloning the repository |

### Optional (for specific features)

| Requirement | Purpose | Install Command |
|-------------|---------|-----------------|
| Chrome/Chromium | EPUB to XTC conversion | (usually pre-installed) |
| ChromeDriver | EPUB to XTC conversion | `brew install chromedriver` |
| Tk 8.6 | GUI support | See [GUI Setup](#gui-setup-tk-86-requirement) |

## Quick Install

```bash
git clone https://github.com/michaelrichey-personal/ereader-sync.git
cd ereader-sync
uv sync                # Install dependencies (use 'uv sync --extra gui' for GUI)
cp config/secrets.config.template config/secrets.config
# Edit config/secrets.config with your WiFi passwords
./ereader-tui          # Run the terminal interface
```

Don't have uv? Install it: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Detailed Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/michaelrichey-personal/ereader-sync.git
cd ereader-sync
```

### Step 2: Set Up Python Environment

#### Option A: Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer. It's significantly faster than pip.

**Install uv:**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via Homebrew
brew install uv

# Or via pip
pip install uv
```

**Install dependencies:**
```bash
# Install all dependencies (creates .venv automatically)
uv sync

# Activate the virtual environment
source .venv/bin/activate

# Optional: Install GUI support
uv sync --extra gui

# Optional: Install development tools
uv sync --extra dev
```

#### Option B: Using pip

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Optional: Install GUI support
pip install customtkinter>=5.2.0

# Optional: Install development tools
pip install pytest black ruff
```

#### Option C: Using pyenv (for managing Python versions)

```bash
# Install pyenv if you don't have it
brew install pyenv pyenv-virtualenv

# Install Python 3.12.12
pyenv install 3.12.12

# Create a virtualenv for this project
pyenv virtualenv 3.12.12 ereaderenv

# Activate it
pyenv activate ereaderenv

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure the Application

```bash
# Copy the secrets template
cp config/secrets.config.template config/secrets.config

# Edit the secrets file with your passwords
nano config/secrets.config  # or use your preferred editor
```

**Required secrets (in `config/secrets.config`):**
```bash
# WiFi password for your e-paper device's network
EPAPER_NETWORK_PASSWORD=your_epaper_wifi_password

# WiFi password for your home/original network
ORIGINAL_NETWORK_PASSWORD=your_home_wifi_password
```

**Optional: Customize application settings (in `config/application.config`):**
```bash
# E-paper device settings
EPAPER_DEVICE_IP=192.168.4.1
EPAPER_NETWORK=your_epaper_network_name

# Scraper settings
NUM_HACKADAY_ARTICLES=10
NUM_HCR_POSTS=5
NUM_HN_STORIES=20

# And many more - see the file for all options
```

### Step 4: Install ChromeDriver (Optional)

Only needed if you want to convert EPUB files to XTC format.

**macOS:**
```bash
brew install chromedriver

# If you get a security warning, allow it in System Preferences
# Or run: xattr -d com.apple.quarantine $(which chromedriver)
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install chromium-chromedriver
```

**Linux (Fedora):**
```bash
sudo dnf install chromedriver
```

**Verify installation:**
```bash
chromedriver --version
```

## Platform-Specific Instructions

### macOS

**Homebrew dependencies (recommended):**
```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install useful tools
brew install python@3.12 uv chromedriver
```

**WiFi switching:** Works out of the box using `networksetup` command.

### Linux

**Debian/Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install python3 python3-venv python3-pip chromium-chromedriver
```

**Fedora:**
```bash
sudo dnf install python3 python3-pip chromedriver
```

**WiFi switching:** Not currently supported (macOS only).

### Windows

**Note:** WiFi switching and the bash scripts won't work on Windows. You can still use the scrapers and TUI.

```powershell
# Install Python from python.org or Microsoft Store

# Clone and setup
git clone https://github.com/michaelrichey-personal/ereader-sync.git
cd ereader-sync

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## GUI Setup (Tk 8.6 Requirement)

**Important:** The GUI requires Python built with **Tk 8.6**, not Tk 9.0.

Tk 9.0 has a critical bug on macOS that completely breaks mousewheel and trackpad scrolling.

### Check Your Tk Version

```bash
python3 -c "import tkinter; print(f'Tk version: {tkinter.TclVersion}')"
```

- Output `8.6` = Good, GUI will work
- Output `9.0` = GUI scrolling will be broken

### If You Have Tk 9.0

**Option 1: Use the TUI instead (easiest)**

The TUI has all the same features as the GUI and doesn't require tkinter:
```bash
./ereader-tui
```

**Option 2: Install Python with Tk 8.6 (pyenv)**

```bash
# 1. Install Tk 8.6
brew install tcl-tk@8

# 2. Temporarily link Tk 8.6 (required during Python build)
brew unlink tcl-tk 2>/dev/null  # Ignore error if not installed
brew link tcl-tk@8 --force

# 3. Install Python 3.12.12
pyenv install 3.12.12

# 4. Verify Tk version
~/.pyenv/versions/3.12.12/bin/python3 -c "import tkinter; print(tkinter.TclVersion)"
# Should output: 8.6

# 5. Create virtualenv with this Python
pyenv virtualenv 3.12.12 ereaderenv
pyenv activate ereaderenv
pip install -r requirements.txt
pip install customtkinter>=5.2.0

# 6. (Optional) Relink Tk 9.0 for other projects
# brew unlink tcl-tk@8
# brew link tcl-tk
```

**Option 3: Manual Python build with Tk 8.6**

If the above doesn't work:

```bash
# Install Tk 8.6
brew install tcl-tk@8

# Build Python with explicit Tk 8.6 paths
PYTHON_CONFIGURE_OPTS="--with-tcltk-includes='-I/usr/local/opt/tcl-tk@8/include' --with-tcltk-libs='-L/usr/local/opt/tcl-tk@8/lib -ltcl8.6 -ltk8.6'" \
  pyenv install 3.12.12

# Verify
~/.pyenv/versions/3.12.12/bin/python3 -c "import tkinter; print(tkinter.TclVersion)"
```

**Option 4: Use system Python**

macOS system Python often has tkinter built-in:
```bash
/usr/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install customtkinter>=5.2.0
```

## Verifying Installation

Run these commands to verify everything is set up correctly:

```bash
# Check Python version
python3 --version
# Expected: Python 3.9.x - 3.13.x

# Check dependencies are installed
python3 -c "import requests, bs4, ebooklib; print('Core deps OK')"

# Check TUI dependencies
python3 -c "import textual; print('TUI deps OK')"

# Check GUI dependencies (optional)
python3 -c "import customtkinter; print('GUI deps OK')"

# Check Tk version (for GUI)
python3 -c "import tkinter; print(f'Tk: {tkinter.TclVersion}')"
# Should be 8.6 for GUI to work properly

# Check ChromeDriver (for conversion)
chromedriver --version

# Check config files exist
ls config/application.config config/secrets.config

# Run the TUI
./ereader-tui
```

## Troubleshooting

### "No module named 'requests'" (or other import errors)

Make sure you've activated the virtual environment:
```bash
source .venv/bin/activate
# Then try again
```

### "No module named '_tkinter'"

Your Python wasn't built with tkinter support. Options:
1. Use the TUI instead: `./ereader-tui`
2. Install Python with tkinter (see [GUI Setup](#gui-setup-tk-86-requirement))
3. Use system Python: `/usr/bin/python3 -m venv .venv`

### ChromeDriver version mismatch

ChromeDriver must match your Chrome version:
```bash
# Check Chrome version
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

# Check ChromeDriver version
chromedriver --version

# Update ChromeDriver if needed
brew upgrade chromedriver
```

### "secrets.config not found"

You need to create the secrets file:
```bash
cp config/secrets.config.template config/secrets.config
# Edit with your passwords
```

### Permission denied running scripts

Make the launcher scripts executable:
```bash
chmod +x ereader-gui ereader-tui bin/*.sh
```

### uv sync fails

```bash
# Remove lock file and try again
rm uv.lock
uv sync
```

### WiFi switching doesn't work

- WiFi switching only works on macOS
- Verify network names in `config/application.config`
- Verify passwords in `config/secrets.config`
- Check your WiFi interface name: `networksetup -listallhardwareports`

## Updating

To update to the latest version:

```bash
# Pull latest changes
git pull

# Update dependencies
source .venv/bin/activate

# With uv
uv sync

# With pip
pip install -r requirements.txt --upgrade
```

## Uninstalling

```bash
# Remove the virtual environment
rm -rf .venv

# Remove the repository
cd ..
rm -rf ereader-sync

# Optional: Remove uv
rm ~/.cargo/bin/uv

# Optional: Remove pyenv virtualenv
pyenv virtualenv-delete ereaderenv
```
