#!/usr/bin/env python3
"""
CustomTkinter GUI for E-Reader content management system.
Modern, lightweight alternative to Kivy.
"""

import logging
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

try:
    import customtkinter as ctk
except ImportError:
    print("Error: CustomTkinter is not installed.")
    print("Install it with: pip install customtkinter")
    print("\nOr use the TUI instead: ./ereader-tui")
    sys.exit(1)

from bin.config_reader import get_repo_root, read_config_file
from bin.utils.ui_helpers import (
    check_chromedriver_available,
    discover_scrapers,
    get_all_config_categories,
    load_epub_files,
    parse_progress_line,
    save_application_config,
    save_secrets_config,
)

# Set up detailed logging for debugging scrolling issues
log_file = os.path.join(os.path.dirname(__file__), "..", "gui_scroll_debug.log")
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w",  # Overwrite log each time
)
logging.info("=" * 80)
logging.info(f"GUI Started - Python {sys.version}")
logging.info(f"Platform: {sys.platform}")
logging.info(
    f"CustomTkinter version: {ctk.__version__ if hasattr(ctk, '__version__') else 'unknown'}"
)
logging.info("=" * 80)


# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"


def enable_mousewheel_scrolling(widget):
    """Enable mouse wheel and trackpad scrolling for CustomTkinter scrollable frames.

    This fixes scroll issues on macOS with trackpads and mouse wheels.
    Binds directly to the canvas instead of using bind_all for better reliability.
    """
    if isinstance(widget, ctk.CTkScrollableFrame):
        canvas = widget._parent_canvas
        widget_name = widget.__class__.__name__

        logging.info(f"Setting up scrolling for {widget_name}")
        logging.info(f"  Canvas: {canvas}")

        def _on_mousewheel(event):
            # Log every scroll event with details
            logging.debug("SCROLL EVENT")
            logging.debug(f"  Widget: {event.widget}")
            logging.debug(f"  Delta: {event.delta}")

            # macOS/Windows - use delta value divided by 120 for smooth scrolling
            # On macOS, trackpad sends values that need to be normalized
            try:
                # Check if there's actually content to scroll
                if canvas.yview() != (0.0, 1.0):  # Only scroll if not showing all content
                    scroll_amount = int(-1 * (event.delta / 120))
                    if scroll_amount != 0:  # Only scroll if delta is non-zero
                        logging.debug(f"  Scrolling by {scroll_amount} units")
                        canvas.yview_scroll(scroll_amount, "units")
                        logging.debug("  ✓ Scroll successful")
                else:
                    logging.debug("  No scroll needed - all content visible")
            except Exception as e:
                logging.error(f"  ✗ Scroll failed: {e}")
            return "break"  # Prevent event propagation

        def _bound_to_mousewheel(event):
            # When mouse enters, bind mousewheel directly to canvas
            logging.debug("Mouse entered - binding mousewheel to canvas")
            canvas.bind("<MouseWheel>", _on_mousewheel, add="+")

        def _unbound_to_mousewheel(event):
            # When mouse leaves, unbind mousewheel from canvas
            logging.debug("Mouse left - unbinding mousewheel from canvas")
            canvas.unbind("<MouseWheel>")

        # Bind enter/leave events to the scrollable frame itself
        logging.info("  Binding <Enter> to enable mousewheel")
        widget.bind("<Enter>", _bound_to_mousewheel)

        logging.info("  Binding <Leave> to disable mousewheel")
        widget.bind("<Leave>", _unbound_to_mousewheel)

        # Also bind to the canvas directly so scrolling works even without enter/leave
        canvas.bind("<Enter>", _bound_to_mousewheel, add="+")
        canvas.bind("<Leave>", _unbound_to_mousewheel, add="+")

        # Also bind to all children so scrolling works anywhere in the frame
        child_count = 0

        def bind_children(parent):
            nonlocal child_count
            for child in parent.winfo_children():
                try:
                    child.bind("<Enter>", _bound_to_mousewheel, add="+")
                    child.bind("<Leave>", _unbound_to_mousewheel, add="+")
                    child_count += 1
                    bind_children(child)
                except Exception as e:
                    logging.warning(f"  Failed to bind to child {child}: {e}")

        bind_children(widget)
        logging.info(f"  Bound enter/leave to {child_count} child widgets")

    # Also recursively enable for any nested scrollable frames
    try:
        for child in widget.winfo_children():
            enable_mousewheel_scrolling(child)
    except Exception:
        pass


class SettingsTab(ctk.CTkScrollableFrame):
    """Settings tab for editing application configuration."""

    def __init__(self, master, **kwargs):
        logging.info(f"SettingsTab.__init__ called with master={master}")
        super().__init__(master, **kwargs)
        logging.info(f"  After super().__init__: self.master={self.master}")
        logging.info(f"  self._parent_canvas={self._parent_canvas}")
        self.config_inputs = {}
        self.load_settings()

    def _render_category(self, category_name, keys, config):
        """Render a single category of settings.

        Args:
            category_name: Display name for the category
            keys: List of config keys in this category
            config: Dict of all config values
        """
        # Category header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(15, 5))

        header = ctk.CTkLabel(
            header_frame, text=category_name, font=ctk.CTkFont(size=14, weight="bold")
        )
        header.pack(anchor="w")

        # Settings in this category
        for key in keys:
            if key in config:
                setting_frame = ctk.CTkFrame(self, fg_color="transparent")
                setting_frame.pack(fill="x", padx=20, pady=2)

                label = ctk.CTkLabel(setting_frame, text=f"{key}:", width=250, anchor="w")
                label.pack(side="left", padx=(0, 10))

                entry = ctk.CTkEntry(setting_frame, width=300)
                entry.insert(0, str(config[key]))
                entry.pack(side="left", fill="x", expand=True)

                self.config_inputs[key] = entry

    def load_settings(self):
        """Load settings from config file."""
        # Clear existing widgets
        for widget in self.winfo_children():
            widget.destroy()
        self.config_inputs.clear()

        # Title
        title = ctk.CTkLabel(
            self, text="Application Settings", font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=10)

        # Theme selector (always visible at top)
        theme_frame = ctk.CTkFrame(self)
        theme_frame.pack(fill="x", padx=20, pady=10)

        theme_label = ctk.CTkLabel(theme_frame, text="Theme:", width=100, anchor="w")
        theme_label.pack(side="left", padx=10)

        # Get current theme from config or default to dark
        try:
            config_temp = read_config_file("application.config")
            current_theme = config_temp.get("GUI_THEME", "dark")
        except Exception:
            current_theme = "dark"

        self.theme_selector = ctk.CTkSegmentedButton(
            theme_frame, values=["light", "dark"], command=self.change_theme
        )
        self.theme_selector.set(current_theme)
        self.theme_selector.pack(side="left", padx=10)

        try:
            config = read_config_file("application.config")
            core_categories, scraper_categories = get_all_config_categories(config)

            # Section: Core Settings
            section_header = ctk.CTkLabel(
                self,
                text="Core Settings",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=("gray20", "gray80"),
            )
            section_header.pack(anchor="w", padx=10, pady=(15, 5))

            for category_name, keys in core_categories.items():
                self._render_category(category_name, keys, config)

            # Section: Scraper Settings (auto-detected)
            if scraper_categories:
                separator = ctk.CTkFrame(self, height=2, fg_color=("gray70", "gray30"))
                separator.pack(fill="x", padx=20, pady=(20, 10))

                section_header = ctk.CTkLabel(
                    self,
                    text="Scraper Settings",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=("gray20", "gray80"),
                )
                section_header.pack(anchor="w", padx=10, pady=(5, 5))

                section_note = ctk.CTkLabel(
                    self,
                    text="(Auto-detected from configuration file)",
                    font=ctk.CTkFont(size=11, slant="italic"),
                    text_color=("gray50", "gray60"),
                )
                section_note.pack(anchor="w", padx=10, pady=(0, 10))

                for category_name, keys in scraper_categories.items():
                    self._render_category(category_name, keys, config)

        except Exception as e:
            error_label = ctk.CTkLabel(self, text=f"Error loading config: {e}", text_color="red")
            error_label.pack(pady=10)

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", pady=20, padx=10)

        reload_btn = ctk.CTkButton(button_frame, text="Reload", command=self.load_settings)
        reload_btn.pack(side="left", padx=5)

        save_btn = ctk.CTkButton(button_frame, text="Save Settings", command=self.save_settings)
        save_btn.pack(side="left", padx=5)

        # Enable mouse wheel scrolling (with delay to ensure all widgets are loaded)
        self.after(200, lambda: enable_mousewheel_scrolling(self))

    def save_settings(self):
        """Save settings to config file."""
        # Collect all config values from input widgets
        config_values = {}
        for key, input_widget in self.config_inputs.items():
            config_values[key] = input_widget.get()

        # Add theme from theme selector
        if hasattr(self, "theme_selector"):
            config_values["GUI_THEME"] = self.theme_selector.get()

        # Use shared save function
        success, message = save_application_config(config_values)

        # Show message
        if success:
            self.show_message(message, "green")
        else:
            self.show_message(message, "red")

    def change_theme(self, theme):
        """Change the application theme."""
        ctk.set_appearance_mode(theme)

        # Update the config file
        try:
            # Read current config
            config = read_config_file("application.config")
            config["GUI_THEME"] = theme

            # Use shared save function
            save_application_config(config)

        except Exception as e:
            print(f"Error saving theme: {e}")

    def show_message(self, message, color):
        """Show a temporary message."""
        msg_label = ctk.CTkLabel(self, text=message, text_color=color)
        msg_label.pack(pady=5)
        self.after(3000, msg_label.destroy)


class SecretsTab(ctk.CTkFrame):
    """Secrets tab for editing sensitive configuration."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.secret_inputs = {}
        self.load_secrets()

    def load_secrets(self):
        """Load secrets from config file."""
        # Clear existing widgets
        for widget in self.winfo_children():
            widget.destroy()
        self.secret_inputs.clear()

        # Title
        title = ctk.CTkLabel(
            self, text="Secrets Configuration", font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=10)

        # Warning
        warning = ctk.CTkLabel(
            self, text="⚠️  Sensitive Information - Do not share these values", text_color="orange"
        )
        warning.pack(pady=5)

        try:
            config = read_config_file("secrets.config")

            for key, value in sorted(config.items()):
                setting_frame = ctk.CTkFrame(self, fg_color="transparent")
                setting_frame.pack(fill="x", padx=20, pady=5)

                label = ctk.CTkLabel(setting_frame, text=f"{key}:", width=250, anchor="w")
                label.pack(side="left", padx=(0, 10))

                entry = ctk.CTkEntry(setting_frame, width=300, show="*")
                entry.insert(0, str(value))
                entry.pack(side="left", fill="x", expand=True)

                self.secret_inputs[key] = entry

        except FileNotFoundError:
            info_label = ctk.CTkLabel(
                self, text="secrets.config not found - will be created on save", text_color="yellow"
            )
            info_label.pack(pady=10)
        except Exception as e:
            error_label = ctk.CTkLabel(self, text=f"Error loading secrets: {e}", text_color="red")
            error_label.pack(pady=10)

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", pady=20, padx=10)

        reload_btn = ctk.CTkButton(button_frame, text="Reload", command=self.load_secrets)
        reload_btn.pack(side="left", padx=5)

        save_btn = ctk.CTkButton(button_frame, text="Save Secrets", command=self.save_secrets)
        save_btn.pack(side="left", padx=5)

    def save_secrets(self):
        """Save secrets to file."""
        # Collect all secret values from input widgets
        secrets_values = {}
        for key, entry in self.secret_inputs.items():
            secrets_values[key] = entry.get()

        # Use shared save function
        success, message = save_secrets_config(secrets_values)

        # Show message
        if success:
            self.show_message(message, "green")
        else:
            self.show_message(message, "red")

    def show_message(self, message, color):
        """Show a temporary message."""
        msg_label = ctk.CTkLabel(self, text=message, text_color=color)
        msg_label.pack(pady=5)
        self.after(3000, msg_label.destroy)


class GenerateTab(ctk.CTkFrame):
    """Content generation tab."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.scraper_vars = {}  # {scraper_name: BooleanVar}
        self.scrapers = []  # [(name, path)]
        self.setup_ui()

    def setup_ui(self):
        """Set up the UI."""
        # Title
        title = ctk.CTkLabel(
            self, text="Generate Content", font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=10)

        # Discover scrapers
        self.scrapers = discover_scrapers()

        # Options
        options_frame = ctk.CTkFrame(self)
        options_frame.pack(fill="x", padx=20, pady=10)

        if self.scrapers:
            for display_name, script_path, source_name in self.scrapers:
                var = ctk.BooleanVar(value=True)
                self.scraper_vars[source_name] = (var, script_path, display_name)

                checkbox = ctk.CTkCheckBox(
                    options_frame, text=f"Scrape {display_name}", variable=var
                )
                checkbox.pack(anchor="w", padx=10, pady=5)
        else:
            # No scrapers found
            label = ctk.CTkLabel(
                options_frame,
                text="No scrapers found in bin/scrapers/\nSee SCRAPER_SPEC.md for how to add scrapers",
                text_color="orange",
            )
            label.pack(anchor="w", padx=10, pady=5)

        # Generate button
        gen_btn = ctk.CTkButton(self, text="Generate Content", command=self.generate_content)
        gen_btn.pack(pady=10)

        # Status section
        status_frame = ctk.CTkFrame(self)
        status_frame.pack(fill="x", padx=20, pady=10)

        self.status_label = ctk.CTkLabel(status_frame, text="Ready to generate content", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=5)

        self.progress_bar = ctk.CTkProgressBar(status_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)

        # Output toggle
        output_header = ctk.CTkFrame(self, fg_color="transparent")
        output_header.pack(fill="x", padx=20)

        output_label = ctk.CTkLabel(output_header, text="Details:", anchor="w")
        output_label.pack(side="left")

        self.show_output_var = ctk.BooleanVar(value=False)
        self.toggle_output_btn = ctk.CTkButton(
            output_header, text="Show Details", command=self.toggle_output, width=120
        )
        self.toggle_output_btn.pack(side="right", padx=5)

        self.output_text = ctk.CTkTextbox(self, height=150)
        self.output_text.pack(fill="both", expand=True, padx=20, pady=5)
        self.output_text.pack_forget()  # Hide by default

    def toggle_output(self):
        """Toggle the visibility of the output textbox."""
        if self.show_output_var.get():
            self.output_text.pack_forget()
            self.toggle_output_btn.configure(text="Show Details")
            self.show_output_var.set(False)
        else:
            self.output_text.pack(fill="both", expand=True, padx=20, pady=5)
            self.toggle_output_btn.configure(text="Hide Details")
            self.show_output_var.set(True)

    def run_script_with_progress(self, script_path, script_name):
        """Run a script and parse progress output in real-time."""
        repo_root = get_repo_root()
        try:
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                cwd=repo_root,
            )

            # Read stdout line by line
            for line in iter(process.stdout.readline, ""):
                if not line:
                    break

                # Check if it's a progress line
                progress_data = parse_progress_line(line.strip())
                if progress_data:
                    successful, failures, processed, total, current_item = progress_data
                    # Update progress bar
                    if total > 0:
                        progress = processed / total
                        self.after(0, lambda p=progress: self.progress_bar.set(p))
                    # Update status label
                    status_text = f"{current_item} ({processed}/{total})"
                    self.after(
                        0,
                        lambda t=status_text: self.status_label.configure(
                            text=t, text_color="white"
                        ),
                    )
                else:
                    # Regular output line - display it
                    self.append_output(line)

            # Wait for process to complete
            process.wait()

            # Read any stderr
            stderr = process.stderr.read()
            if stderr:
                self.append_output(f"\nErrors: {stderr}\n")

            return process.returncode == 0

        except Exception as e:
            self.append_output(f"Error running {script_name}: {e}\n")
            return False

    def generate_content(self):
        """Generate content in background thread."""
        # Check if any scrapers are selected
        selected_scrapers = [
            (name, path, display)
            for name, (var, path, display) in self.scraper_vars.items()
            if var.get()
        ]

        if not selected_scrapers:
            self.after(
                0,
                lambda: self.status_label.configure(
                    text="Error: No scrapers selected!", text_color="red"
                ),
            )
            return

        # Reset UI
        self.output_text.delete("1.0", "end")
        self.after(
            0,
            lambda: self.status_label.configure(
                text=f"Starting {len(selected_scrapers)} scraper(s) in parallel...",
                text_color="white",
            ),
        )
        self.after(0, lambda: self.progress_bar.set(0))

        def run():
            results = {}
            scraper_count = len(selected_scrapers)

            # Run scrapers in parallel
            with ThreadPoolExecutor(max_workers=scraper_count) as executor:
                futures = {}
                for source_name, script_path, display_name in selected_scrapers:
                    self.append_output(f"\n--- Starting {display_name} scraper ---\n")
                    future = executor.submit(
                        self.run_script_with_progress, script_path, display_name
                    )
                    futures[future] = display_name

                # Collect results as they complete
                completed = 0
                for future in futures:
                    display_name = futures[future]
                    try:
                        success = future.result()
                        results[display_name] = success
                        completed += 1
                        # Update progress bar
                        progress = completed / scraper_count
                        self.after(0, lambda p=progress: self.progress_bar.set(p))
                    except Exception as e:
                        results[display_name] = False
                        self.append_output(f"\nError in {display_name}: {e}\n")
                        completed += 1

            # Final status
            successful = sum(1 for s in results.values() if s)
            failed = len(results) - successful

            if failed == 0:
                self.after(
                    0,
                    lambda: self.status_label.configure(
                        text=f"✓ All {successful} scraper(s) completed!", text_color="green"
                    ),
                )
                self.after(0, lambda: self.progress_bar.set(1.0))
            else:
                self.after(
                    0,
                    lambda: self.status_label.configure(
                        text=f"✗ {successful} succeeded, {failed} failed",
                        text_color="orange",
                    ),
                )

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def append_output(self, text):
        """Append text to output (thread-safe)."""
        self.after(0, lambda: self.output_text.insert("end", text))
        self.after(0, lambda: self.output_text.see("end"))


class ConvertTab(ctk.CTkFrame):
    """EPUB to XTC conversion tab."""

    def __init__(self, master, sync_tab=None, **kwargs):
        super().__init__(master, **kwargs)
        self.file_checkboxes = {}
        self.sync_tab = sync_tab
        self.chromedriver_available, self.chromedriver_message = check_chromedriver_available()
        self.setup_ui()

    def setup_ui(self):
        """Set up the UI."""
        # Title
        title = ctk.CTkLabel(
            self, text="Convert EPUB to XTC", font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=10)

        # Check if chromedriver is available
        if not self.chromedriver_available:
            # Show unavailable message
            unavailable_frame = ctk.CTkFrame(self)
            unavailable_frame.pack(fill="both", expand=True, padx=20, pady=20)

            warning_label = ctk.CTkLabel(
                unavailable_frame,
                text="Conversion Unavailable",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=("red", "#FF6B6B"),
            )
            warning_label.pack(pady=(20, 10))

            message_label = ctk.CTkLabel(
                unavailable_frame,
                text=self.chromedriver_message,
                wraplength=500,
                justify="left",
            )
            message_label.pack(pady=10, padx=20)

            # Add a hint about restarting
            hint_label = ctk.CTkLabel(
                unavailable_frame,
                text="After installing, restart the application.",
                text_color=("gray40", "gray60"),
            )
            hint_label.pack(pady=(10, 20))
            return

        # Info
        info = ctk.CTkLabel(
            self,
            text="Convert EPUB files to XTC format for XTeink devices. Requires Chrome/Chromium browser.",
            wraplength=600,
        )
        info.pack(pady=5)

        # Attribution
        attribution_frame = ctk.CTkFrame(self, fg_color="transparent")
        attribution_frame.pack(fill="x", padx=20, pady=5)

        attribution_text = ctk.CTkLabel(
            attribution_frame,
            text="Powered by x4converter.rho.sh - Thanks to Lukasz!",
            text_color=("gray40", "gray60"),
        )
        attribution_text.pack(side="left")

        support_link = ctk.CTkButton(
            attribution_frame,
            text="Support his work",
            command=lambda: __import__("webbrowser").open("https://buymeacoffee.com/ukasz"),
            width=120,
            height=24,
            fg_color="transparent",
            text_color=("#1E88E5", "#64B5F6"),
            hover_color=("gray90", "gray20"),
        )
        support_link.pack(side="left", padx=10)

        # File list label
        files_label = ctk.CTkLabel(self, text="Select EPUBs to convert:", anchor="w")
        files_label.pack(fill="x", padx=20, pady=(10, 5))

        # Selection buttons (above file list)
        top_btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_btn_frame.pack(fill="x", padx=20, pady=(0, 5))

        select_all_btn = ctk.CTkButton(top_btn_frame, text="Select All", command=self.select_all)
        select_all_btn.pack(side="left", padx=5)

        select_none_btn = ctk.CTkButton(top_btn_frame, text="Select None", command=self.select_none)
        select_none_btn.pack(side="left", padx=5)

        # File list
        self.file_frame = ctk.CTkScrollableFrame(self, height=200)
        self.file_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # Action buttons (below file list)
        bottom_btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_btn_frame.pack(fill="x", padx=20, pady=5)

        refresh_btn = ctk.CTkButton(bottom_btn_frame, text="Refresh List", command=self.load_files)
        refresh_btn.pack(side="left", padx=5)

        convert_btn = ctk.CTkButton(
            bottom_btn_frame, text="Convert to XTC", command=self.convert_files
        )
        convert_btn.pack(side="left", padx=5)

        # Status section
        status_frame = ctk.CTkFrame(self)
        status_frame.pack(fill="x", padx=20, pady=10)

        self.status_label = ctk.CTkLabel(status_frame, text="Ready", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=5)

        self.progress_bar = ctk.CTkProgressBar(status_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)

        # Output toggle
        output_header = ctk.CTkFrame(self, fg_color="transparent")
        output_header.pack(fill="x", padx=20)

        output_label = ctk.CTkLabel(output_header, text="Details:", anchor="w")
        output_label.pack(side="left")

        self.show_output_var = ctk.BooleanVar(value=False)
        self.toggle_output_btn = ctk.CTkButton(
            output_header, text="Show Details", command=self.toggle_output, width=120
        )
        self.toggle_output_btn.pack(side="right", padx=5)

        self.output_text = ctk.CTkTextbox(self, height=150)
        self.output_text.pack(fill="both", expand=True, padx=20, pady=5)
        self.output_text.pack_forget()  # Hide by default
        self.output_text.insert(
            "1.0",
            "Ready to convert EPUBs to XTC...\nNote: Conversion settings can be configured in the Settings tab.\n",
        )

        # Load files
        self.load_files()

    def toggle_output(self):
        """Toggle the visibility of the output textbox."""
        if self.show_output_var.get():
            self.output_text.pack_forget()
            self.toggle_output_btn.configure(text="Show Details")
            self.show_output_var.set(False)
        else:
            self.output_text.pack(fill="both", expand=True, padx=20, pady=5)
            self.toggle_output_btn.configure(text="Hide Details")
            self.show_output_var.set(True)

    def load_files(self):
        """Load EPUB files from texts directory."""
        # Clear existing
        for widget in self.file_frame.winfo_children():
            widget.destroy()
        self.file_checkboxes.clear()

        try:
            # Use shared load function (filter to .epub only)
            epub_files, error = load_epub_files(file_extension=".epub")

            if error:
                label = ctk.CTkLabel(self.file_frame, text=error)
                label.pack()
                return

            if not epub_files:
                label = ctk.CTkLabel(
                    self.file_frame, text="No EPUB files found. Generate content first."
                )
                label.pack()
                return

            # Create checkboxes
            for rel_path, full_path, size_kb in epub_files:
                var = ctk.BooleanVar(value=True)
                checkbox = ctk.CTkCheckBox(
                    self.file_frame, text=f"{rel_path} ({size_kb:.1f} KB)", variable=var
                )
                checkbox.pack(anchor="w", padx=10, pady=2)
                self.file_checkboxes[full_path] = var

        except Exception as e:
            label = ctk.CTkLabel(self.file_frame, text=f"Error: {e}")
            label.pack()

        # Enable mouse wheel scrolling
        self.after(200, lambda: enable_mousewheel_scrolling(self.file_frame))

    def select_all(self):
        """Select all files."""
        for var in self.file_checkboxes.values():
            var.set(True)

    def select_none(self):
        """Deselect all files."""
        for var in self.file_checkboxes.values():
            var.set(False)

    def convert_files(self):
        """Convert selected files."""
        selected = [path for path, var in self.file_checkboxes.items() if var.get()]

        if not selected:
            self.after(
                0,
                lambda: self.status_label.configure(
                    text="Error: No files selected!", text_color="red"
                ),
            )
            self.after(0, lambda: self.progress_bar.set(0))
            return

        # Reset UI
        self.output_text.delete("1.0", "end")
        self.after(
            0,
            lambda: self.status_label.configure(
                text=f"Starting conversion of {len(selected)} file(s)...", text_color="white"
            ),
        )
        self.after(0, lambda: self.progress_bar.set(0))

        def run():
            repo_root = get_repo_root()
            script_path = os.path.join(repo_root, "bin", "converters", "convert_epub_to_xtc.py")

            try:
                cmd = [sys.executable, script_path] + selected
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,  # Line buffered
                    cwd=repo_root,
                )

                # Read stdout line by line in real-time
                for line in iter(process.stdout.readline, ""):
                    if not line:
                        break

                    # Check if it's a progress line
                    progress_data = parse_progress_line(line.strip())
                    if progress_data:
                        successful, failures, processed, total, current_item = progress_data
                        # Update progress bar
                        if total > 0:
                            progress = processed / total
                            self.after(0, lambda p=progress: self.progress_bar.set(p))
                        # Update status label
                        status_text = f"{current_item} ({processed}/{total})"
                        self.after(
                            0,
                            lambda t=status_text: self.status_label.configure(
                                text=t, text_color="white"
                            ),
                        )
                    else:
                        # Regular output line - display it
                        self.append_output(line)

                # Wait for process to complete
                process.wait()

                # Read any stderr
                stderr = process.stderr.read()
                if stderr:
                    self.append_output(f"\nErrors: {stderr}\n")

                # Final status
                if process.returncode == 0:
                    self.after(
                        0,
                        lambda: self.status_label.configure(
                            text="✓ Conversion complete!", text_color="green"
                        ),
                    )
                    self.after(0, lambda: self.progress_bar.set(1.0))
                    self.after(1000, self.load_files)  # Refresh file list
                    # Also refresh the sync tab if available
                    if self.sync_tab:
                        self.after(1000, self.sync_tab.load_files)
                else:
                    self.after(
                        0,
                        lambda: self.status_label.configure(
                            text=f"✗ Conversion failed (exit code {process.returncode})",
                            text_color="red",
                        ),
                    )
                    self.after(0, lambda: self.progress_bar.set(0))

            except Exception as e:
                error_msg = f"Error during conversion: {e}"
                self.append_output(error_msg + "\n")
                self.after(
                    0, lambda: self.status_label.configure(text=f"✗ {error_msg}", text_color="red")
                )
                self.after(0, lambda: self.progress_bar.set(0))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def append_output(self, text):
        """Append text to output (thread-safe)."""
        self.after(0, lambda: self.output_text.insert("end", text))
        self.after(0, lambda: self.output_text.see("end"))


class SyncTab(ctk.CTkFrame):
    """Sync to e-reader tab."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.file_checkboxes = {}
        self.setup_ui()

    def setup_ui(self):
        """Set up the UI."""
        # Title
        title = ctk.CTkLabel(
            self, text="Sync to E-Reader", font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=10)

        # Info
        info = ctk.CTkLabel(
            self,
            text="Note: WiFi switching may need permissions. Uncheck WiFi option if it fails.",
            wraplength=600,
        )
        info.pack(pady=5)

        # Options
        options_frame = ctk.CTkFrame(self)
        options_frame.pack(fill="x", padx=20, pady=10)

        self.wifi_var = ctk.BooleanVar(value=True)
        wifi_check = ctk.CTkCheckBox(
            options_frame, text="Auto-switch WiFi network", variable=self.wifi_var
        )
        wifi_check.pack(anchor="w", padx=10, pady=5)

        # File list label
        files_label = ctk.CTkLabel(self, text="Select files to sync:", anchor="w")
        files_label.pack(fill="x", padx=20, pady=(10, 5))

        # Selection buttons (above file list)
        top_btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_btn_frame.pack(fill="x", padx=20, pady=(0, 5))

        select_all_btn = ctk.CTkButton(top_btn_frame, text="Select All", command=self.select_all)
        select_all_btn.pack(side="left", padx=5)

        select_none_btn = ctk.CTkButton(top_btn_frame, text="Select None", command=self.select_none)
        select_none_btn.pack(side="left", padx=5)

        # File list
        self.file_frame = ctk.CTkScrollableFrame(self, height=200)
        self.file_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # Action buttons (below file list)
        bottom_btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_btn_frame.pack(fill="x", padx=20, pady=5)

        refresh_btn = ctk.CTkButton(bottom_btn_frame, text="Refresh List", command=self.load_files)
        refresh_btn.pack(side="left", padx=5)

        sync_btn = ctk.CTkButton(bottom_btn_frame, text="Sync to E-Reader", command=self.sync_files)
        sync_btn.pack(side="left", padx=5)

        # Status section
        status_frame = ctk.CTkFrame(self)
        status_frame.pack(fill="x", padx=20, pady=10)

        self.status_label = ctk.CTkLabel(status_frame, text="Ready to sync content", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=5)

        self.progress_bar = ctk.CTkProgressBar(status_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)

        # Output toggle
        output_header = ctk.CTkFrame(self, fg_color="transparent")
        output_header.pack(fill="x", padx=20)

        output_label = ctk.CTkLabel(output_header, text="Details:", anchor="w")
        output_label.pack(side="left")

        self.show_output_var = ctk.BooleanVar(value=False)
        self.toggle_output_btn = ctk.CTkButton(
            output_header, text="Show Details", command=self.toggle_output, width=120
        )
        self.toggle_output_btn.pack(side="right", padx=5)

        self.output_text = ctk.CTkTextbox(self, height=150)
        self.output_text.pack(fill="both", expand=True, padx=20, pady=5)
        self.output_text.pack_forget()  # Hide by default

        # Load files
        self.load_files()

    def toggle_output(self):
        """Toggle the visibility of the output textbox."""
        if self.show_output_var.get():
            self.output_text.pack_forget()
            self.toggle_output_btn.configure(text="Show Details")
            self.show_output_var.set(False)
        else:
            self.output_text.pack(fill="both", expand=True, padx=20, pady=5)
            self.toggle_output_btn.configure(text="Hide Details")
            self.show_output_var.set(True)

    def load_files(self):
        """Load EPUB and XTC files from texts directory."""
        # Clear existing
        for widget in self.file_frame.winfo_children():
            widget.destroy()
        self.file_checkboxes.clear()

        try:
            # Use shared load function (loads both .epub and .xtc files)
            ebook_files, error = load_epub_files(file_extension=None)

            if error:
                label = ctk.CTkLabel(self.file_frame, text=error)
                label.pack()
                return

            if not ebook_files:
                label = ctk.CTkLabel(
                    self.file_frame, text="No EPUB or XTC files found. Generate content first."
                )
                label.pack()
                return

            # Create checkboxes
            for rel_path, full_path, size_kb in ebook_files:
                var = ctk.BooleanVar(value=True)
                checkbox = ctk.CTkCheckBox(
                    self.file_frame, text=f"{rel_path} ({size_kb:.1f} KB)", variable=var
                )
                checkbox.pack(anchor="w", padx=10, pady=2)
                self.file_checkboxes[full_path] = var

        except Exception as e:
            label = ctk.CTkLabel(self.file_frame, text=f"Error: {e}")
            label.pack()

        # Enable mouse wheel scrolling
        self.after(200, lambda: enable_mousewheel_scrolling(self.file_frame))

    def select_all(self):
        """Select all files."""
        for var in self.file_checkboxes.values():
            var.set(True)

    def select_none(self):
        """Deselect all files."""
        for var in self.file_checkboxes.values():
            var.set(False)

    def sync_files(self):
        """Sync selected files to e-reader."""
        selected = [path for path, var in self.file_checkboxes.items() if var.get()]

        if not selected:
            self.after(
                0,
                lambda: self.status_label.configure(
                    text="Error: No files selected!", text_color="red"
                ),
            )
            self.after(0, lambda: self.progress_bar.set(0))
            return

        # Reset UI
        self.output_text.delete("1.0", "end")
        self.after(
            0,
            lambda: self.status_label.configure(
                text=f"Starting sync of {len(selected)} file(s)...", text_color="white"
            ),
        )
        self.after(0, lambda: self.progress_bar.set(0))

        def run():
            repo_root = get_repo_root()

            try:
                # Pass the current Python executable to child processes
                env = os.environ.copy()
                env["EREADER_PYTHON"] = sys.executable

                if self.wifi_var.get():
                    self.after(
                        0,
                        lambda: self.status_label.configure(
                            text="Switching to E-Paper WiFi network...", text_color="white"
                        ),
                    )
                    script_path = os.path.join(repo_root, "bin", "switch_to_epaper_wifi.sh")
                    cmd = ["bash", script_path] + selected
                else:
                    self.after(
                        0,
                        lambda: self.status_label.configure(
                            text="Uploading files...", text_color="white"
                        ),
                    )
                    script_path = os.path.join(repo_root, "bin", "upload_to_epaper.py")
                    cmd = [sys.executable, script_path] + selected

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,  # Line buffered
                    cwd=repo_root,
                    env=env,
                )

                # Read stdout line by line in real-time
                for line in iter(process.stdout.readline, ""):
                    if not line:
                        break

                    # Check if it's a progress line
                    progress_data = parse_progress_line(line.strip())
                    if progress_data:
                        successful, failures, processed, total, current_item = progress_data
                        # Update progress bar
                        if total > 0:
                            progress = processed / total
                            self.after(0, lambda p=progress: self.progress_bar.set(p))
                        # Update status label
                        status_text = f"{current_item} ({processed}/{total})"
                        self.after(
                            0,
                            lambda t=status_text: self.status_label.configure(
                                text=t, text_color="white"
                            ),
                        )
                    else:
                        # Regular output line - display it
                        self.append_output(line)

                # Wait for process to complete
                process.wait()

                # Read any stderr
                stderr = process.stderr.read()
                if stderr:
                    self.append_output(f"\nErrors: {stderr}\n")

                # Final status
                if process.returncode == 0:
                    self.after(
                        0,
                        lambda: self.status_label.configure(
                            text="✓ Sync complete!", text_color="green"
                        ),
                    )
                    self.after(0, lambda: self.progress_bar.set(1.0))
                else:
                    self.after(
                        0,
                        lambda: self.status_label.configure(
                            text=f"✗ Sync failed (exit code {process.returncode})", text_color="red"
                        ),
                    )
                    self.after(0, lambda: self.progress_bar.set(0))

            except Exception as e:
                error_msg = f"Error during sync: {e}"
                self.append_output(error_msg + "\n")
                self.after(
                    0, lambda: self.status_label.configure(text=f"✗ {error_msg}", text_color="red")
                )
                self.after(0, lambda: self.progress_bar.set(0))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def append_output(self, text):
        """Append text to output (thread-safe)."""
        self.after(0, lambda: self.output_text.insert("end", text))
        self.after(0, lambda: self.output_text.see("end"))


class EReaderApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Load and apply theme from config
        try:
            config = read_config_file("application.config")
            theme = config.get("GUI_THEME", "dark")
            ctk.set_appearance_mode(theme)
        except Exception:
            ctk.set_appearance_mode("dark")  # Default to dark

        # Configure window
        self.title("E-Reader Manager")
        self.geometry("900x700")

        # Create tabview
        self.tabview = ctk.CTkTabview(self, command=self.on_tab_change)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        # Create bottom frame for quit button
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=10, pady=10)

        # Add quit button to bottom right
        quit_button = ctk.CTkButton(
            bottom_frame,
            text="Quit",
            command=self.quit_application,
            width=100,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
        )
        quit_button.pack(side="right")

        # Add tabs
        self.tabview.add("Settings")
        self.tabview.add("Secrets")
        self.tabview.add("Generate")
        self.tabview.add("Convert")
        self.tabview.add("Sync")

        # Create tab content
        self.settings_tab = SettingsTab(self.tabview.tab("Settings"))
        self.settings_tab.pack(fill="both", expand=True)

        self.secrets_tab = SecretsTab(self.tabview.tab("Secrets"))
        self.secrets_tab.pack(fill="both", expand=True)

        self.generate_tab = GenerateTab(self.tabview.tab("Generate"))
        self.generate_tab.pack(fill="both", expand=True)

        self.convert_tab = ConvertTab(self.tabview.tab("Convert"))
        self.convert_tab.pack(fill="both", expand=True)

        self.sync_tab = SyncTab(self.tabview.tab("Sync"))
        self.sync_tab.pack(fill="both", expand=True)

        # Connect convert tab to sync tab for auto-refresh
        self.convert_tab.sync_tab = self.sync_tab

    def on_tab_change(self):
        """Handle tab changes - refresh file lists when switching to Convert or Sync tabs."""
        current_tab = self.tabview.get()
        if current_tab == "Convert":
            self.convert_tab.load_files()
        elif current_tab == "Sync":
            self.sync_tab.load_files()

    def quit_application(self):
        """Gracefully quit the application."""
        self.quit()
        self.destroy()


def main():
    """Entry point for the GUI application."""
    app = EReaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
