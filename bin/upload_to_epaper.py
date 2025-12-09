#!/usr/bin/env python3
"""
Script to upload ebook files to e-paper device.
Supports EPUB, XTC, XTG, XTH, XTCH and other formats. Maintains directory structure from texts/.
By default, files are deleted after successful upload.

Usage:
    upload_to_epaper.py                       # Upload all files (delete after sync)
    upload_to_epaper.py --keep-files          # Upload all files (keep after sync)
    upload_to_epaper.py file1.epub file2.xtc  # Upload specific files
"""

import os
import sys
import time

import requests
from config_reader import get_config, get_repo_root
from utils.common import output_progress, suppress_urllib3_warning

# Suppress urllib3 warning
suppress_urllib3_warning()


# Supported ebook file extensions
SUPPORTED_EXTENSIONS = (".epub", ".xtc", ".xtg", ".xth", ".xtch")


def find_ebook_files(directory):
    """Recursively find all supported ebook files in the directory."""
    ebook_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_EXTENSIONS):
                full_path = os.path.join(root, file)
                ebook_files.append(full_path)

    return ebook_files


def create_folder(folder_path, base_url, upload_timeout):
    """Create a folder on the e-paper device.

    Args:
        folder_path: Path like "/hcr/" or "/hackernews/" (must end with /)
        base_url: Base URL for the edit endpoint
        upload_timeout: Request timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    # Ensure path starts with / and ends with /
    if not folder_path.startswith("/"):
        folder_path = "/" + folder_path
    if not folder_path.endswith("/"):
        folder_path = folder_path + "/"

    try:
        # PUT to /edit with path field to create folder
        # Path ending in / signals it's a folder
        # This matches the server's mkdir.onclick JavaScript function
        data = {"path": folder_path}
        response = requests.put(base_url, data=data, timeout=upload_timeout)

        if response.status_code == 200:
            return True
        else:
            print(f"  Warning: Failed to create folder {folder_path} (HTTP {response.status_code})")
            return False

    except Exception as e:
        print(f"  Warning: Error creating folder {folder_path}: {e}")
        return False


def upload_file(file_path, relative_path, target_url, upload_timeout):
    """Upload a single file to the e-paper device.

    Args:
        file_path: Absolute path to the file on local system
        relative_path: Relative path on device (e.g., "hcr/file.epub")
        target_url: URL to upload to
        upload_timeout: Request timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    filename = os.path.basename(file_path)

    # The target path on the device (with subdirectory)
    target_path = "/" + relative_path.replace("\\", "/")

    # Determine MIME type based on extension
    if filename.lower().endswith((".xtc", ".xtg", ".xth", ".xtch")):
        mime_type = "application/octet-stream"
    else:
        mime_type = "application/epub+zip"

    print(f"Uploading: {relative_path} ...", end=" ")

    try:
        # Open the file
        with open(file_path, "rb") as f:
            # Create form data matching the web interface format
            # From the HTML: formData.append("data", file, path)
            files = {"data": (target_path, f, mime_type)}

            # POST to /edit endpoint
            response = requests.post(target_url, files=files, timeout=upload_timeout)

            if response.status_code == 200:
                print("✓ Success")
                return True
            else:
                print(f"✗ Failed (HTTP {response.status_code})")
                print(f"  Response: {response.text[:100]}")
                return False

    except requests.exceptions.RequestException as e:
        print(f"✗ Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def main():
    """Main function to find and upload ebook files."""
    print("=" * 60)
    print("E-Book Uploader for E-Paper Device")
    print("=" * 60)

    # Load configuration
    config = get_config()
    repo_root = get_repo_root()

    # Directory to search (relative to repository root)
    texts_dir = os.path.join(repo_root, config["TEXTS_DIR"])

    # Check if directory exists
    if not os.path.exists(texts_dir):
        print(f"Error: Directory not found: {texts_dir}")
        return

    # Build target URL
    target_url = f"http://{config['EPAPER_DEVICE_IP']}{config['EPAPER_UPLOAD_ENDPOINT']}"

    # Parse arguments
    args = sys.argv[1:]
    keep_files = False

    if "--keep-files" in args:
        keep_files = True
        args.remove("--keep-files")

    # Determine which files to upload
    if args:
        # Specific files provided as arguments
        print("\nUploading specific files provided as arguments")
        ebook_files = []
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

            if os.path.exists(file_path) and file_path.lower().endswith(SUPPORTED_EXTENSIONS):
                ebook_files.append(file_path)
            else:
                print(f"Warning: File not found or unsupported format: {arg}")
    else:
        # Find all supported ebook files
        print(f"\nSearching for ebook files in: {texts_dir}")
        ebook_files = find_ebook_files(texts_dir)

    if not ebook_files:
        print("No EPUB or XTC files to upload!")
        return

    # Build list of (file_path, relative_path) tuples
    file_info = []
    for file_path in ebook_files:
        if file_path.startswith(texts_dir):
            rel_path = os.path.relpath(file_path, texts_dir)
        else:
            rel_path = os.path.basename(file_path)
        file_info.append((file_path, rel_path))

    print(f"\nFound {len(file_info)} e-book file(s) to upload:\n")
    for i, (file_path, rel_path) in enumerate(file_info, 1):
        size = os.path.getsize(file_path)
        size_kb = size / 1024
        print(f"  {i}. {rel_path} ({size_kb:.1f} KB)")

    # Extract unique subdirectories that need to be created
    folders_to_create = set()
    for file_path, rel_path in file_info:
        # Get directory part of relative path
        dir_path = os.path.dirname(rel_path)
        if dir_path:  # Only if file is in a subdirectory
            # Build path components
            parts = dir_path.split(os.sep)
            current_path = ""
            for part in parts:
                if current_path:
                    current_path = current_path + "/" + part
                else:
                    current_path = part
                folders_to_create.add(current_path)

    # Create folders on device
    total_files = len(file_info)
    success_count = 0
    fail_count = 0

    # Output initial progress
    output_progress(0, 0, 0, total_files, "Starting upload to e-paper device")

    if folders_to_create:
        print("\n" + "=" * 60)
        print(f"Creating {len(folders_to_create)} folder(s) on device")
        print("=" * 60 + "\n")

        for folder in sorted(folders_to_create):
            output_progress(
                success_count, fail_count, 0, total_files, f"Creating folder: /{folder}/"
            )
            print(f"Creating folder: /{folder}/ ...", end=" ")
            if create_folder(folder, target_url, config["UPLOAD_TIMEOUT"]):
                print("✓")
            else:
                print("(may already exist)")
            time.sleep(0.5)  # Small delay between folder creations

    print("\n" + "=" * 60)
    print(f"Starting upload to {target_url}")
    if keep_files:
        print("Files will be kept after upload")
    else:
        print("Files will be deleted after successful upload")
    print("=" * 60 + "\n")

    # Track successfully uploaded files for deletion
    uploaded_files = []

    # Upload each file
    for i, (file_path, rel_path) in enumerate(file_info, 1):
        output_progress(success_count, fail_count, i - 1, total_files, f"Uploading: {rel_path}")
        print(f"[{i}/{total_files}] ", end="")

        if upload_file(file_path, rel_path, target_url, config["UPLOAD_TIMEOUT"]):
            success_count += 1
            uploaded_files.append((file_path, rel_path))
        else:
            fail_count += 1

        # Small delay between uploads to avoid overwhelming the device
        if i < total_files:
            time.sleep(config["UPLOAD_DELAY_SECONDS"])

    # Final progress
    output_progress(success_count, fail_count, success_count + fail_count, total_files, "Complete")

    # Delete successfully uploaded files (unless --keep-files was specified)
    deleted_count = 0
    if not keep_files and uploaded_files:
        print("\n" + "=" * 60)
        print("Cleaning up uploaded files")
        print("=" * 60 + "\n")

        for file_path, rel_path in uploaded_files:
            try:
                os.remove(file_path)
                print(f"  Deleted: {rel_path}")
                deleted_count += 1
            except Exception as e:
                print(f"  Warning: Could not delete {rel_path}: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("Upload Summary")
    print("=" * 60)
    print(f"Total files: {total_files}")
    print(f"Uploaded: {success_count}")
    print(f"Failed: {fail_count}")
    if not keep_files:
        print(f"Deleted: {deleted_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
