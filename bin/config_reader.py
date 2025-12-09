#!/usr/bin/env python3
"""
Utility module to read configuration files.
"""

import os


def read_config_file(filename):
    """Read a config file and return a dictionary of key-value pairs."""
    config = {}

    # Find config directory relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    config_path = os.path.join(repo_root, "config", filename)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse key=value pairs
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Convert numeric values and booleans
                if value.isdigit():
                    config[key] = int(value)
                elif value.lower() in ("true", "false"):
                    config[key] = value.lower() == "true"
                else:
                    # Try to parse as float
                    try:
                        config[key] = float(value)
                    except ValueError:
                        config[key] = value

    return config


def get_config():
    """Get merged application and secrets configuration."""
    app_config = read_config_file("application.config")

    try:
        secrets_config = read_config_file("secrets.config")
        app_config.update(secrets_config)
    except FileNotFoundError:
        print("Warning: secrets.config not found, continuing without secrets")

    return app_config


def get_repo_root():
    """Get the repository root directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)
