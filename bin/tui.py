#!/usr/bin/env python3
"""
Textual TUI for E-Reader content management system.
"""

import asyncio
import os
import sys

from bin.config_reader import get_repo_root, read_config_file
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    Log,
    TabbedContent,
    TabPane,
)
from bin.utils.ui_helpers import (
    discover_scrapers,
    get_all_config_categories,
    load_epub_files,
    parse_progress_line,
    save_application_config,
    save_secrets_config,
)

try:
    import pyperclip

    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False


class SettingsPane(VerticalScroll):
    """Settings configuration pane."""

    def __init__(self):
        super().__init__()
        self.config_inputs = {}

    def compose(self) -> ComposeResult:
        """Compose the settings pane."""
        yield Label("Application Settings", classes="title")
        yield Label("Edit configuration values below:", classes="subtitle")

        # Theme selector
        with Horizontal(id="theme_selector"):
            yield Label("Theme:", classes="setting-label")
            yield Button("Dark Theme", id="theme_dark", variant="default")
            yield Button("Light Theme", id="theme_light", variant="default")

        try:
            config = read_config_file("application.config")
            core_categories, scraper_categories = get_all_config_categories(config)

            # Section: Core Settings
            yield Label("Core Settings", classes="section-header")

            for category_name, keys in core_categories.items():
                yield Label(f"{category_name}", classes="category-header")
                for key in keys:
                    if key in config:
                        with Horizontal(classes="setting-row"):
                            yield Label(f"{key}:", classes="setting-label")
                            input_widget = Input(value=str(config[key]), id=f"setting_{key}")
                            self.config_inputs[key] = input_widget
                            yield input_widget

            # Section: Scraper Settings (auto-detected)
            if scraper_categories:
                yield Label("", classes="section-separator")
                yield Label("Scraper Settings", classes="section-header")
                yield Label("(Auto-detected from configuration file)", classes="section-note")

                for category_name, keys in scraper_categories.items():
                    yield Label(f"{category_name}", classes="category-header")
                    for key in keys:
                        if key in config:
                            with Horizontal(classes="setting-row"):
                                yield Label(f"{key}:", classes="setting-label")
                                input_widget = Input(value=str(config[key]), id=f"setting_{key}")
                                self.config_inputs[key] = input_widget
                                yield input_widget

        except Exception as e:
            yield Label(f"Error loading config: {e}", classes="error")

        with Horizontal(classes="button-row"):
            yield Button("Save Settings", id="save_settings", variant="primary")
            yield Button("Reload", id="reload_settings")

    def save_config(self):
        """Save configuration to file."""
        # Collect all config values from input widgets
        config_values = {}

        # Get all categories dynamically
        config = read_config_file("application.config")
        core_categories, scraper_categories = get_all_config_categories(config)

        # Collect from core categories
        for category, keys in core_categories.items():
            for key in keys:
                input_id = f"setting_{key}"
                try:
                    input_widget = self.query_one(f"#{input_id}", Input)
                    if input_widget:
                        config_values[key] = input_widget.value
                except Exception:
                    pass  # Widget not found, skip

        # Collect from scraper categories
        for category, keys in scraper_categories.items():
            for key in keys:
                input_id = f"setting_{key}"
                try:
                    input_widget = self.query_one(f"#{input_id}", Input)
                    if input_widget:
                        config_values[key] = input_widget.value
                except Exception:
                    pass  # Widget not found, skip

        # Use shared save function
        return save_application_config(config_values)


class SecretsPane(VerticalScroll):
    """Secrets configuration pane."""

    def __init__(self):
        super().__init__()
        self.secret_inputs = {}

    def compose(self) -> ComposeResult:
        """Compose the secrets pane."""
        yield Label("Secrets Configuration", classes="title")
        yield Label("⚠️  Sensitive Information - Do not share these values", classes="warning")

        try:
            config = read_config_file("secrets.config")

            for key, value in sorted(config.items()):
                with Horizontal(classes="setting-row"):
                    yield Label(f"{key}:", classes="setting-label")
                    input_widget = Input(value=str(value), password=True, id=f"secret_{key}")
                    self.secret_inputs[key] = input_widget
                    yield input_widget

        except FileNotFoundError:
            yield Label("secrets.config not found - will be created on save", classes="info")
        except Exception as e:
            yield Label(f"Error loading secrets: {e}", classes="error")

        with Horizontal(classes="button-row"):
            yield Button("Save Secrets", id="save_secrets", variant="primary")
            yield Button("Reload", id="reload_secrets")

    def save_secrets(self):
        """Save secrets to file."""
        # Collect all secret values from input widgets
        secrets_values = {}
        for key in self.secret_inputs.keys():
            input_id = f"secret_{key}"
            try:
                input_widget = self.query_one(f"#{input_id}", Input)
                if input_widget:
                    secrets_values[key] = input_widget.value
            except Exception:
                pass  # Widget not found, skip

        # Use shared save function
        return save_secrets_config(secrets_values)


class GeneratePane(Container):
    """Content generation pane."""

    def __init__(self, *args, **kwargs):
        """Initialize the generate pane."""
        super().__init__(*args, **kwargs)
        self.scrapers = discover_scrapers()

    def compose(self) -> ComposeResult:
        """Compose the generate pane."""
        yield Label("Generate Content", classes="title")
        yield Label("Select content sources to scrape:", classes="subtitle")

        with Vertical(classes="options"):
            if self.scrapers:
                for display_name, script_path, source_name in self.scrapers:
                    yield Checkbox(
                        f"Scrape {display_name}",
                        value=True,
                        id=f"gen_{source_name}",
                        classes="option-item",
                    )
            else:
                yield Label("No scrapers found in bin/scrapers/", classes="error")
                yield Label("See SCRAPER_SPEC.md for how to add scrapers", classes="info")

        with Horizontal(classes="button-row"):
            yield Button("Generate Content", id="generate_content", variant="primary")

        yield Label("Output:", classes="subtitle")
        yield Log(id="generate_output", auto_scroll=True)

    async def run_single_scraper(self, display_name, script_path, repo_root):
        """Run a single scraper and return (display_name, success, output_lines).

        Args:
            display_name: Human-readable name of the scraper
            script_path: Path to the scraper script
            repo_root: Repository root directory

        Returns:
            Tuple of (display_name, success, output_lines)
        """
        output_lines = []
        success = True

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_root,
            )

            # Read stdout line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                line = line.decode().rstrip()

                # Check if it's a progress line (skip progress lines in output)
                progress_data = parse_progress_line(line)
                if not progress_data:
                    output_lines.append(line)

            await process.wait()

            # Read any remaining stderr
            stderr = await process.stderr.read()
            if stderr:
                output_lines.append(f"Errors: {stderr.decode()}")

            if process.returncode != 0:
                success = False

        except Exception as e:
            output_lines.append(f"Error running {display_name} scraper: {e}")
            success = False

        return (display_name, success, output_lines)

    async def generate_content(self, selected_scrapers):
        """Generate content by running scraper scripts in parallel.

        Args:
            selected_scrapers: List of tuples (display_name, script_path)
        """
        output = self.query_one("#generate_output", Log)
        output.clear()
        output.write_line(f"Starting {len(selected_scrapers)} scraper(s) in parallel...")

        repo_root = get_repo_root()

        # Create tasks for all scrapers
        tasks = [
            self.run_single_scraper(display_name, script_path, repo_root)
            for display_name, script_path in selected_scrapers
        ]

        # Run all scrapers in parallel
        results = await asyncio.gather(*tasks)

        # Output results for each scraper
        successful = 0
        failed = 0
        for display_name, success, lines in results:
            output.write_line(f"\n--- {display_name} ---")
            for line in lines:
                output.write_line(line)
            if success:
                output.write_line(f"✓ {display_name} completed successfully")
                successful += 1
            else:
                output.write_line(f"✗ {display_name} failed")
                failed += 1

        # Final summary
        if failed == 0:
            output.write_line(f"\n=== All {successful} scraper(s) completed! ===")
        else:
            output.write_line(f"\n=== {successful} succeeded, {failed} failed ===")


class SyncPane(Container):
    """E-reader sync pane."""

    def __init__(self, *args, **kwargs):
        """Initialize the sync pane."""
        super().__init__(*args, **kwargs)
        self.file_paths = []  # Store file paths separately from widget IDs

    def compose(self) -> ComposeResult:
        """Compose the sync pane."""
        yield Label("Sync to E-Reader", classes="title")
        yield Label("Upload files to your e-paper device", classes="subtitle")

        with Vertical(classes="options"):
            yield Checkbox(
                "Auto-switch WiFi network", value=True, id="sync_wifi", classes="option-item"
            )

        yield Label("Select files to sync:", classes="subtitle")

        # File selection area with scrolling
        with VerticalScroll(id="file_scroll"):
            yield Container(id="file_list")

        # Selection buttons
        with Horizontal(classes="button-row"):
            yield Button("Select All", id="select_all_files")
            yield Button("Select None", id="select_none_files")
            yield Button("Refresh List", id="refresh_files")

        yield Button("Sync to E-Reader", id="sync_content", variant="primary")

        yield Label("Output:", classes="subtitle")
        yield Log(id="sync_output", auto_scroll=True)

    def on_mount(self) -> None:
        """Load files when pane is mounted."""
        self.load_epub_files()

    def load_epub_files(self):
        """Load list of EPUB and XTC files from texts directory."""
        file_container = self.query_one("#file_list", Container)
        file_container.remove_children()
        self.file_paths = []  # Reset file paths

        # Use shared load function (loads both .epub and .xtc files)
        ebook_files, error = load_epub_files(file_extension=None)

        if error:
            file_container.mount(Label(error))
            return

        if not ebook_files:
            file_container.mount(Label("No EPUB or XTC files found. Generate content first."))
            return

        # Create checkbox for each file with index-based ID
        for idx, (rel_path, full_path, size_kb) in enumerate(ebook_files):
            self.file_paths.append(full_path)  # Store path at index
            checkbox = Checkbox(f"{rel_path} ({size_kb:.1f} KB)", value=True, id=f"sync_file_{idx}")
            file_container.mount(checkbox)

    def get_selected_files(self):
        """Get list of selected file paths."""
        selected = []
        file_container = self.query_one("#file_list", Container)
        for widget in file_container.children:
            if isinstance(widget, Checkbox) and widget.value:
                # Extract index from widget id (format: sync_file_N)
                try:
                    idx = int(widget.id.replace("sync_file_", ""))
                    if 0 <= idx < len(self.file_paths):
                        selected.append(self.file_paths[idx])
                except (ValueError, IndexError):
                    pass  # Skip invalid IDs
        return selected

    async def sync_content(self, wifi_switch: bool):
        """Sync content to e-reader."""
        output = self.query_one("#sync_output", Log)
        output.clear()

        selected_files = self.get_selected_files()

        if not selected_files:
            output.write_line("Error: No files selected!")
            return

        output.write_line("Starting sync...")
        output.write_line(f"Syncing {len(selected_files)} selected file(s)\n")

        repo_root = get_repo_root()

        # Pass the current Python executable to child processes
        env = os.environ.copy()
        env["EREADER_PYTHON"] = sys.executable

        try:
            if wifi_switch:
                output.write_line("Using WiFi auto-switch script...")
                script_path = os.path.join(repo_root, "bin", "switch_to_epaper_wifi.sh")
                # Pass selected files as arguments
                process = await asyncio.create_subprocess_exec(
                    "bash",
                    script_path,
                    *selected_files,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=repo_root,
                    env=env,
                )
            else:
                output.write_line("Uploading directly (no WiFi switch)...")
                script_path = os.path.join(repo_root, "bin", "upload_to_epaper.py")
                # Pass selected files as arguments
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    script_path,
                    *selected_files,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=repo_root,
                    env=env,
                )

            # Read stdout line by line in real-time
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                line = line.decode().rstrip()

                # Check if it's a progress line
                progress_data = parse_progress_line(line)
                if not progress_data:
                    # Regular output - display it
                    output.write_line(line)

            await process.wait()

            # Read any remaining stderr
            stderr = await process.stderr.read()
            if stderr:
                for line in stderr.decode().split("\n"):
                    if line.strip():
                        output.write_line(f"[stderr] {line}")

            if process.returncode == 0:
                output.write_line("\n=== Sync complete! ===")
            else:
                output.write_line(f"\n=== Sync failed with code {process.returncode} ===")

        except Exception as e:
            output.write_line(f"Error during sync: {e}")


class ConvertPane(Container):
    """EPUB to XTC conversion pane."""

    def __init__(self, *args, **kwargs):
        """Initialize the convert pane."""
        super().__init__(*args, **kwargs)
        self.file_paths = []  # Store file paths separately from widget IDs

    def compose(self) -> ComposeResult:
        """Compose the convert pane."""
        yield Label("Convert EPUB to XTC", classes="title")
        yield Label(
            "Convert EPUB files to XTC format for XTeink devices. Requires Chrome/Chromium browser.",
            classes="info",
        )
        yield Label(
            "Powered by x4converter.rho.sh - Thanks to Lukasz! Support: https://buymeacoffee.com/ukasz",
            classes="attribution",
        )

        yield Label("Select EPUBs to convert:", classes="subtitle")

        # File selection area with scrolling
        with VerticalScroll(id="convert_file_scroll"):
            yield Container(id="convert_file_list")

        # Selection buttons
        with Horizontal(classes="button-row"):
            yield Button("Select All", id="convert_select_all_files")
            yield Button("Select None", id="convert_select_none_files")
            yield Button("Refresh List", id="convert_refresh_files")

        yield Button("Convert to XTC", id="convert_files", variant="primary")

        yield Label("Output:", classes="subtitle")
        yield Log(id="convert_output", auto_scroll=True)

    def on_mount(self) -> None:
        """Load files when pane is mounted."""
        self.load_epub_files()

    def load_epub_files(self):
        """Load list of EPUB files from texts directory."""
        file_container = self.query_one("#convert_file_list", Container)
        file_container.remove_children()
        self.file_paths = []  # Reset file paths

        # Use shared load function (filter to .epub only)
        epub_files, error = load_epub_files(file_extension=".epub")

        if error:
            file_container.mount(Label(error))
            return

        if not epub_files:
            file_container.mount(Label("No EPUB files found. Generate content first."))
            return

        # Create checkbox for each file with index-based ID
        for idx, (rel_path, full_path, size_kb) in enumerate(epub_files):
            self.file_paths.append(full_path)  # Store path at index
            checkbox = Checkbox(
                f"{rel_path} ({size_kb:.1f} KB)", value=True, id=f"convert_file_{idx}"
            )
            file_container.mount(checkbox)

    def get_selected_files(self):
        """Get list of selected file paths."""
        selected = []
        file_container = self.query_one("#convert_file_list", Container)
        for widget in file_container.children:
            if isinstance(widget, Checkbox) and widget.value:
                # Extract index from widget id (format: convert_file_N)
                try:
                    idx = int(widget.id.replace("convert_file_", ""))
                    if 0 <= idx < len(self.file_paths):
                        selected.append(self.file_paths[idx])
                except (ValueError, IndexError):
                    pass  # Skip invalid IDs
        return selected

    async def convert_files(self):
        """Convert selected EPUB files to XTC format."""
        output = self.query_one("#convert_output", Log)
        output.clear()

        selected_files = self.get_selected_files()

        if not selected_files:
            output.write_line("Error: No files selected!")
            return

        output.write_line("Starting conversion...")
        output.write_line(f"Converting {len(selected_files)} selected file(s)\n")

        repo_root = get_repo_root()

        try:
            script_path = os.path.join(repo_root, "bin", "converters", "convert_epub_to_xtc.py")

            # Pass selected files as arguments
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                script_path,
                *selected_files,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_root,
            )

            # Read stdout line by line in real-time
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                line = line.decode().rstrip()

                # Check if it's a progress line
                progress_data = parse_progress_line(line)
                if not progress_data:
                    # Regular output - display it
                    output.write_line(line)

            await process.wait()

            # Read any remaining stderr
            stderr = await process.stderr.read()
            if stderr:
                for line in stderr.decode().split("\n"):
                    if line.strip():
                        output.write_line(f"[stderr] {line}")

            if process.returncode == 0:
                output.write_line("\n=== Conversion complete! ===")
                # Refresh file list to show new files
                self.load_epub_files()
                # Also refresh sync pane if available
                try:
                    sync_pane = self.app.query_one(SyncPane)
                    sync_pane.load_epub_files()
                except Exception:
                    pass
            else:
                output.write_line(f"\n=== Conversion failed with code {process.returncode} ===")

        except Exception as e:
            output.write_line(f"Error during conversion: {e}")


class EReaderTUI(App):
    """Textual TUI for E-Reader management."""

    CSS = """
    Screen {
        background: $surface;
    }

    .title {
        text-style: bold;
        color: $primary;
        margin: 0 0 1 0;
        padding: 0 1;
    }

    .subtitle {
        color: $text-muted;
        margin: 0 0 0 1;
        padding: 0;
    }

    .section-header {
        color: $primary;
        text-style: bold;
        padding: 0 1;
        margin: 2 0 0 0;
        border-bottom: solid $primary;
    }

    .section-note {
        color: $text-muted;
        text-style: italic;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    .section-separator {
        height: 1;
        margin: 1 0;
    }

    .category-header {
        color: $secondary;
        text-style: bold;
        background: $boost;
        padding: 0 1;
        margin: 1 0 0 0;
    }

    .warning {
        color: #dc3545;
        text-style: bold;
        margin: 0 1;
        background: $boost;
        padding: 1;
    }

    .error {
        color: $error;
        margin: 0 1;
    }

    .info {
        color: $primary;
        margin: 0 1 1 1;
    }

    .attribution {
        color: $text-muted;
        text-style: italic;
        margin: 0 1 1 1;
    }

    .setting-row {
        height: auto;
        margin: 0;
        padding: 0 1;
    }

    .setting-label {
        width: 35;
        padding-right: 2;
    }

    Input {
        width: 1fr;
    }

    .button-row {
        height: auto;
        margin: 1 0;
        padding: 0 1;
    }

    Button {
        margin: 0 1;
    }

    Button.primary {
        margin: 1;
        width: 100%;
    }

    #sync_content, #convert_files {
        margin: 1;
        width: auto;
    }

    .options {
        margin: 1;
        padding: 1;
        border: solid $primary;
        height: auto;
        background: $boost;
    }

    .option-item {
        margin: 0;
        padding: 0 1;
    }

    Log {
        min-height: 8;
        max-height: 15;
        border: solid $primary;
        margin: 1;
        background: $surface-darken-1;
    }

    #file_scroll {
        height: 12;
        border: solid $primary;
        margin: 1;
        background: $surface-darken-1;
    }

    #file_list {
        height: auto;
    }

    #convert_file_scroll {
        height: 12;
        border: solid $primary;
        margin: 1;
        background: $surface-darken-1;
    }

    #convert_file_list {
        height: auto;
    }

    #theme_selector {
        margin: 1 1 2 1;
        padding: 1;
        background: $boost;
        border: solid $primary;
        height: auto;
    }

    #theme_dark, #theme_light {
        margin: 0 1;
        min-width: 16;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 1;
    }

    Checkbox {
        margin: 0;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("c", "copy_log", "Copy Output", show=True),
        Binding("t", "toggle_theme", "Toggle Theme", show=True),
        Binding("s", "screenshot", "Screenshot", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Compose the TUI layout."""
        yield Header()

        with TabbedContent():
            with TabPane("Settings"):
                yield SettingsPane()

            with TabPane("Secrets"):
                yield SecretsPane()

            with TabPane("Generate"):
                yield GeneratePane()

            with TabPane("Convert"):
                yield ConvertPane()

            with TabPane("Sync"):
                yield SyncPane()

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "save_settings":
            pane = self.query_one(SettingsPane)
            success, message = pane.save_config()
            self.notify(message, severity="information" if success else "error")

        elif button_id == "reload_settings":
            self.notify("Reloading settings... (restart TUI to see changes)")

        elif button_id == "theme_dark":
            self.theme = "textual-dark"
            self.notify("Switched to dark theme")

        elif button_id == "theme_light":
            self.theme = "textual-light"
            self.notify("Switched to light theme")

        elif button_id == "save_secrets":
            pane = self.query_one(SecretsPane)
            success, message = pane.save_secrets()
            self.notify(message, severity="information" if success else "error")

        elif button_id == "reload_secrets":
            self.notify("Reloading secrets... (restart TUI to see changes)")

        elif button_id == "generate_content":
            pane = self.query_one(GeneratePane)
            # Collect selected scrapers
            selected = []
            for display_name, script_path, source_name in pane.scrapers:
                try:
                    checkbox = self.query_one(f"#gen_{source_name}", Checkbox)
                    if checkbox.value:
                        selected.append((display_name, script_path))
                except Exception:
                    pass  # Checkbox not found, skip

            if selected:
                self.run_worker(pane.generate_content(selected))
            else:
                self.notify("No scrapers selected!", severity="error")

        elif button_id == "sync_content":
            wifi = self.query_one("#sync_wifi", Checkbox).value
            pane = self.query_one(SyncPane)
            self.run_worker(pane.sync_content(wifi))

        elif button_id == "select_all_files":
            pane = self.query_one(SyncPane)
            file_container = pane.query_one("#file_list", Container)
            for widget in file_container.children:
                if isinstance(widget, Checkbox):
                    widget.value = True
            self.notify("All files selected")

        elif button_id == "select_none_files":
            pane = self.query_one(SyncPane)
            file_container = pane.query_one("#file_list", Container)
            for widget in file_container.children:
                if isinstance(widget, Checkbox):
                    widget.value = False
            self.notify("All files deselected")

        elif button_id == "refresh_files":
            pane = self.query_one(SyncPane)
            pane.load_epub_files()
            self.notify("File list refreshed")

        elif button_id == "convert_files":
            pane = self.query_one(ConvertPane)
            self.run_worker(pane.convert_files())

        elif button_id == "convert_select_all_files":
            pane = self.query_one(ConvertPane)
            file_container = pane.query_one("#convert_file_list", Container)
            for widget in file_container.children:
                if isinstance(widget, Checkbox):
                    widget.value = True
            self.notify("All files selected")

        elif button_id == "convert_select_none_files":
            pane = self.query_one(ConvertPane)
            file_container = pane.query_one("#convert_file_list", Container)
            for widget in file_container.children:
                if isinstance(widget, Checkbox):
                    widget.value = False
            self.notify("All files deselected")

        elif button_id == "convert_refresh_files":
            pane = self.query_one(ConvertPane)
            pane.load_epub_files()
            self.notify("File list refreshed")

    def action_screenshot(self) -> None:
        """Take a screenshot."""
        path = self.save_screenshot()
        self.notify(f"Screenshot saved to {path}")

    def action_copy_log(self) -> None:
        """Copy log output from current tab to clipboard."""
        if not CLIPBOARD_AVAILABLE:
            self.notify("Clipboard support not available. Install pyperclip.", severity="warning")
            return

        try:
            # Try to find a Log widget in the current tab
            log_widgets = self.query(Log)
            if not log_widgets:
                self.notify("No output to copy", severity="warning")
                return

            # Get the first visible Log widget
            for log_widget in log_widgets:
                # Check if the log widget is visible (in current tab)
                if log_widget.display and hasattr(log_widget, "lines"):
                    # Get all lines from the log
                    lines = log_widget.lines
                    if lines:
                        # Join lines and copy to clipboard
                        text = "\n".join(str(line) for line in lines)
                        pyperclip.copy(text)
                        self.notify(
                            f"Copied {len(lines)} lines to clipboard", severity="information"
                        )
                        return

            self.notify("No output to copy", severity="warning")

        except Exception as e:
            self.notify(f"Failed to copy: {e}", severity="error")

    def action_toggle_theme(self) -> None:
        """Toggle between light and dark theme."""
        if self.theme == "textual-dark":
            self.theme = "textual-light"
            self.notify("Switched to light theme", severity="information")
        else:
            self.theme = "textual-dark"
            self.notify("Switched to dark theme", severity="information")

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Handle tab activation - refresh file lists when switching to Convert or Sync tabs."""
        tab_id = event.tab.id
        if tab_id and "convert" in tab_id.lower():
            # Refresh Convert pane file list
            try:
                convert_pane = self.query_one(ConvertPane)
                convert_pane.load_epub_files()
            except Exception:
                pass
        elif tab_id and "sync" in tab_id.lower():
            # Refresh Sync pane file list
            try:
                sync_pane = self.query_one(SyncPane)
                sync_pane.load_epub_files()
            except Exception:
                pass


def main():
    """Entry point for the TUI application."""
    app = EReaderTUI()
    app.run()


if __name__ == "__main__":
    main()
