# Installation Guide

## ⚠️  Important: Tk 8.6 Requirement for GUI

**If you plan to use the GUI (`ereader-gui`), you MUST use Python built with Tk 8.6, not Tk 9.0.**

Tk 9.0 has a critical bug on macOS that completely breaks mousewheel and trackpad scrolling. See the [GUI installation issues section](#gui-installation-issues-on-macos) for setup instructions.

**Quick check:**
```bash
python3 -c "import tkinter; print(f'Tk version: {tkinter.TclVersion}')"
# Should output: Tk version: 8.6 (NOT 9.0)
```

**Recommended Python version:** 3.12.12 (requires-python = ">=3.9,<3.14")

---

## Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver. It's significantly faster than pip and provides better dependency resolution.

### 1. Install uv

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Or via Homebrew:**
```bash
brew install uv
```

**Or via pip:**
```bash
pip install uv
```

### 2. Install Dependencies

**Option A: Install dependencies only (development):**
```bash
# Creates a virtual environment and installs all dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate  # macOS/Linux
```

**Option B: Install in editable mode with command-line scripts:**
```bash
# Install the package in editable mode
uv pip install -e .

# This makes the following commands available:
# - ereader-gui
# - ereader-tui
# - scrape-hcr
# - scrape-hn
# - convert-to-xtc
# - upload-to-epaper
```

**Install with dev dependencies:**
```bash
uv sync --extra dev
```

### 3. Additional Requirements

For EPUB to XTC conversion, you need ChromeDriver:

**macOS:**
```bash
brew install chromedriver
```

**Linux:**
```bash
sudo apt-get install chromium-chromedriver
```

## Using pip (Traditional)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Or install in editable mode
pip install -e .
```

## Verifying Installation

After installation, verify everything works:

```bash
# Check that scripts are available (if installed with -e flag)
ereader-gui --help 2>/dev/null || echo "Use ./ereader-gui instead"
ereader-tui --help 2>/dev/null || echo "Use ./ereader-tui instead"

# Or run scripts directly
python3 bin/scrape_hcr_to_epub.py --help 2>/dev/null || echo "Script ready"
```

## Updating Dependencies

**With uv:**
```bash
# Update all dependencies
uv sync --upgrade

# Update a specific package
uv pip install --upgrade selenium
```

**With pip:**
```bash
pip install --upgrade -r requirements.txt
```

## Troubleshooting

### uv sync fails

If `uv sync` fails, try:
```bash
# Remove existing lock file
rm uv.lock

# Sync again
uv sync
```

### ChromeDriver not found

Make sure ChromeDriver is in your PATH:
```bash
which chromedriver

# If not found, install it:
# macOS: brew install chromedriver
# Linux: sudo apt-get install chromium-chromedriver
```

### GUI installation issues on macOS

**IMPORTANT:** The GUI uses CustomTkinter (modern, lightweight, zero dependency issues).

**⚠️  Tk 9.0 Scrolling Bug:** Tk 9.0 has a critical bug on macOS that breaks mousewheel/trackpad scrolling. You **must** use Python built with Tk 8.6 (not Tk 9.0).

**Recommended Setup for pyenv users:**
```bash
# 1. Install Tk 8.6 (not the default Tk 9.0)
brew install tcl-tk@8

# 2. Temporarily link Tk 8.6
brew unlink tcl-tk
brew link tcl-tk@8 --force

# 3. Install Python 3.12.12 (do not use 3.14+)
pyenv install 3.12.12

# 4. Verify Tk version
~/.pyenv/versions/3.12.12/bin/python3 -c "import tkinter; print(f'Tk version: {tkinter.TclVersion}')"
# Should output: Tk version: 8.6

# 5. Create virtualenv
pyenv virtualenv 3.12.12 ereaderenv
pyenv activate ereaderenv
pip install -e ".[gui]"

# 6. (Optional) Relink Tk 9.0 if you need it for other projects
# brew unlink tcl-tk@8
# brew link tcl-tk
```

**Tkinter missing error:**

If you get `ModuleNotFoundError: No module named '_tkinter'`, your Python wasn't built with tkinter support.

**Manual build with Tk 8.6:**
```bash
# Install tcl-tk@8 first
brew install tcl-tk@8

# Build Python with Tk 8.6 explicitly
PYTHON_CONFIGURE_OPTS="--with-tcltk-includes='-I/usr/local/opt/tcl-tk@8/include' --with-tcltk-libs='-L/usr/local/opt/tcl-tk@8/lib -ltcl8.6 -ltk8.6'" \
  pyenv install 3.12.12

# Verify
~/.pyenv/versions/3.12.12/bin/python3 -c "import tkinter; print(f'Tk: {tkinter.TclVersion}')"
```

**Alternative:** Use the system Python (usually has tkinter built-in):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[gui]"
```

The GUI features:
- Modern dark/light theme support
- Built on CustomTkinter (no SDL2/pygame mess!)
- Uses native tkinter (included with most Python installations)
- Zero compilation required!

### ImportError when running scripts

If you get import errors, make sure you're in the correct directory:
```bash
# Scripts should be run from the repository root
cd /path/to/ereader
python3 bin/script_name.py
```
