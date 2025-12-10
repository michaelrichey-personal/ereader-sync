#!/bin/bash
#
# Script to continuously poll for E-Paper WiFi network availability
# When the network becomes available and there are files to upload,
# automatically triggers the upload script
#

# Get script directory to find config files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$REPO_ROOT/config"

# Load configuration
if [ -f "$CONFIG_DIR/application.config" ]; then
    set -a
    source "$CONFIG_DIR/application.config"
    set +a
else
    echo "ERROR: application.config not found at $CONFIG_DIR/application.config"
    exit 1
fi

# Load secrets for network switching
if [ -f "$CONFIG_DIR/secrets.config" ]; then
    set -a
    source "$CONFIG_DIR/secrets.config"
    set +a
fi

# Configurable poll interval (seconds) - can be overridden via environment variable
POLL_INTERVAL="${POLL_INTERVAL:-5}"

# Auto-upload mode (set to "false" to disable automatic uploads)
AUTO_UPLOAD="${AUTO_UPLOAD:-true}"

# Detect operating system
OS_TYPE="$(uname -s)"

# Detect Linux WiFi backend
LINUX_WIFI_BACKEND=""
if [ "$OS_TYPE" = "Linux" ]; then
    if command -v nmcli &>/dev/null && systemctl is-active --quiet NetworkManager 2>/dev/null; then
        LINUX_WIFI_BACKEND="nmcli"
    elif command -v wpa_cli &>/dev/null && systemctl is-active --quiet wpa_supplicant 2>/dev/null; then
        LINUX_WIFI_BACKEND="wpa_cli"
    elif command -v iwctl &>/dev/null && systemctl is-active --quiet iwd 2>/dev/null; then
        LINUX_WIFI_BACKEND="iwd"
    else
        echo "ERROR: No supported WiFi manager found running on Linux"
        exit 1
    fi
fi

# Determine which Python to use
if [ -n "$EREADER_PYTHON" ]; then
    PYTHON="$EREADER_PYTHON"
elif [ -n "$VIRTUAL_ENV" ]; then
    PYTHON="$VIRTUAL_ENV/bin/python3"
else
    PYTHON="$(which python3 2>/dev/null || command -v python3 2>/dev/null || echo python3)"
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to scan for available networks and check if target is present
is_network_available() {
    local target_network="$1"

    if [ "$OS_TYPE" = "Darwin" ]; then
        # macOS: Use airport to scan for networks
        /System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -s 2>/dev/null | grep -qw "$target_network"
        return $?
    elif [ "$OS_TYPE" = "Linux" ]; then
        case "$LINUX_WIFI_BACKEND" in
            nmcli)
                # Rescan and list available networks
                nmcli device wifi rescan 2>/dev/null
                sleep 1
                nmcli -t -f ssid device wifi list 2>/dev/null | grep -qx "$target_network"
                return $?
                ;;
            wpa_cli)
                # Trigger a scan and check results
                wpa_cli -i "$WIFI_INTERFACE" scan >/dev/null 2>&1
                sleep 2
                wpa_cli -i "$WIFI_INTERFACE" scan_results 2>/dev/null | grep -qw "$target_network"
                return $?
                ;;
            iwd)
                # Scan and check results
                iwctl station "$WIFI_INTERFACE" scan 2>/dev/null
                sleep 2
                iwctl station "$WIFI_INTERFACE" get-networks 2>/dev/null | grep -qw "$target_network"
                return $?
                ;;
        esac
    fi

    return 1
}

# Function to check if there are files to upload in the texts directory
has_files_to_upload() {
    local texts_path="$REPO_ROOT/$TEXTS_DIR"

    if [ ! -d "$texts_path" ]; then
        return 1
    fi

    # Check for .epub or .xtc files recursively
    local file_count
    file_count=$(find "$texts_path" -type f \( -name "*.epub" -o -name "*.xtc" \) 2>/dev/null | wc -l)

    if [ "$file_count" -gt 0 ]; then
        return 0
    else
        return 1
    fi
}

# Function to count files to upload
count_files_to_upload() {
    local texts_path="$REPO_ROOT/$TEXTS_DIR"
    find "$texts_path" -type f \( -name "*.epub" -o -name "*.xtc" \) 2>/dev/null | wc -l | tr -d ' '
}

# Function to run the upload process
run_upload() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo ""
    echo -e "${BLUE}[$timestamp] Starting upload process...${NC}"
    echo "======================================================"

    # Run the switch_to_epaper_wifi.sh script which handles network switching and upload
    "$SCRIPT_DIR/switch_to_epaper_wifi.sh"
    local result=$?

    echo "======================================================"

    if [ $result -eq 0 ]; then
        echo -e "${GREEN}[$timestamp] Upload completed successfully${NC}"
    else
        echo -e "${RED}[$timestamp] Upload failed with exit code $result${NC}"
    fi

    echo ""
    return $result
}

# Track previous state to detect changes
PREVIOUS_STATE="unknown"

# Track if we've already uploaded for this availability window
UPLOADED_THIS_SESSION="false"

echo "======================================================"
echo "E-Paper Network Availability Monitor"
echo "======================================================"
echo "Target network: $EPAPER_NETWORK"
echo "WiFi interface: $WIFI_INTERFACE"
echo "Texts directory: $REPO_ROOT/$TEXTS_DIR"
echo "Poll interval: ${POLL_INTERVAL}s"
echo "Auto-upload: $AUTO_UPLOAD"
echo "Press Ctrl+C to stop"
echo "======================================================"
echo ""

# Initial file check
if has_files_to_upload; then
    FILE_COUNT=$(count_files_to_upload)
    echo -e "${YELLOW}Found $FILE_COUNT file(s) ready for upload${NC}"
else
    echo -e "${YELLOW}No files found in texts directory${NC}"
fi
echo ""

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    if is_network_available "$EPAPER_NETWORK"; then
        CURRENT_STATE="available"
        if [ "$PREVIOUS_STATE" != "available" ]; then
            echo -e "${GREEN}[$TIMESTAMP] ✓ Network '$EPAPER_NETWORK' is now AVAILABLE${NC}"
            UPLOADED_THIS_SESSION="false"

            # Check if we should auto-upload
            if [ "$AUTO_UPLOAD" = "true" ]; then
                if has_files_to_upload; then
                    FILE_COUNT=$(count_files_to_upload)
                    echo -e "${YELLOW}[$TIMESTAMP] Found $FILE_COUNT file(s) to upload${NC}"
                    run_upload
                    UPLOADED_THIS_SESSION="true"
                else
                    echo -e "${YELLOW}[$TIMESTAMP] No files to upload in $TEXTS_DIR${NC}"
                fi
            fi
        fi
    else
        CURRENT_STATE="unavailable"
        if [ "$PREVIOUS_STATE" != "unavailable" ]; then
            echo -e "${RED}[$TIMESTAMP] ✗ Network '$EPAPER_NETWORK' is UNAVAILABLE${NC}"
            UPLOADED_THIS_SESSION="false"
        fi
    fi

    PREVIOUS_STATE="$CURRENT_STATE"

    sleep "$POLL_INTERVAL"
done
