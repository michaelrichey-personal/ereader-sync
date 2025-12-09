#!/bin/bash
#
# Script to switch to Epaper WiFi network, do something, then switch back
#

# Ensure PATH includes standard locations
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Debug: Print environment info
echo "DEBUG: Running as user: $(whoami)"
echo "DEBUG: PATH: $PATH"
echo "DEBUG: networksetup location: $(which networksetup 2>/dev/null || echo 'not in PATH')"

# Get script directory to find config files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$REPO_ROOT/config"

echo "DEBUG: Script dir: $SCRIPT_DIR"
echo "DEBUG: Config dir: $CONFIG_DIR"

# Load configuration from files
echo "DEBUG: Loading application.config from $CONFIG_DIR/application.config"
if [ -f "$CONFIG_DIR/application.config" ]; then
    # Source application config (using set -a to export all variables)
    set -a
    source "$CONFIG_DIR/application.config"
    set +a
    echo "DEBUG: application.config loaded successfully"
else
    echo "ERROR: application.config not found at $CONFIG_DIR/application.config"
    ls -la "$CONFIG_DIR/" 2>&1
    exit 1
fi

echo "DEBUG: Loading secrets.config from $CONFIG_DIR/secrets.config"
if [ -f "$CONFIG_DIR/secrets.config" ]; then
    # Source secrets config
    set -a
    source "$CONFIG_DIR/secrets.config"
    set +a
    echo "DEBUG: secrets.config loaded successfully"
else
    echo "ERROR: secrets.config not found at $CONFIG_DIR/secrets.config"
    ls -la "$CONFIG_DIR/" 2>&1
    exit 1
fi

echo "DEBUG: EPAPER_NETWORK = $EPAPER_NETWORK"
echo "DEBUG: WIFI_INTERFACE = $WIFI_INTERFACE"
echo "DEBUG: PASSWORD length = ${#EPAPER_NETWORK_PASSWORD}"

# Determine which Python to use
# Priority: 1) EREADER_PYTHON (from GUI/TUI), 2) VIRTUAL_ENV, 3) active python3 in PATH
if [ -n "$EREADER_PYTHON" ]; then
    PYTHON="$EREADER_PYTHON"
    echo "DEBUG: Using Python from EREADER_PYTHON: $PYTHON"
elif [ -n "$VIRTUAL_ENV" ]; then
    PYTHON="$VIRTUAL_ENV/bin/python3"
    echo "DEBUG: Using Python from VIRTUAL_ENV: $PYTHON"
else
    # Use whatever python3 is currently active in PATH
    # This will be pyenv's Python if pyenv is active, or system Python otherwise
    PYTHON="$(which python3 2>/dev/null || command -v python3 2>/dev/null || echo python3)"
    echo "DEBUG: Using active Python from PATH: $PYTHON"
fi

# Verify Python has required modules
echo "DEBUG: Verifying Python executable: $PYTHON"
if ! "$PYTHON" -c "import requests" 2>/dev/null; then
    echo "WARNING: Python at $PYTHON does not have 'requests' module installed!"
    echo "WARNING: This may cause upload failures."
    echo "WARNING: Activate your virtualenv or install: pip install -r requirements.txt"
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================================"
echo "Epaper WiFi Network Switcher"
echo "======================================================"
echo "DEBUG: Script starting at $(date)"
echo "DEBUG: Running from directory: $(pwd)"

# Global variables to track state
SWITCHED_TO_EPAPER=false
ORIGINAL_NETWORK=""
TIMEOUT_PID=""

# Emergency reconnect function - always tries to get back to original network
emergency_reconnect() {
    echo ""
    echo "======================================================"
    echo "EMERGENCY RECONNECT TRIGGERED"
    echo "======================================================"

    # Kill timeout process if it exists
    if [ -n "$TIMEOUT_PID" ] && ps -p "$TIMEOUT_PID" > /dev/null 2>&1; then
        kill "$TIMEOUT_PID" 2>/dev/null
    fi

    if [ "$SWITCHED_TO_EPAPER" = true ] && [ -n "$ORIGINAL_NETWORK" ]; then
        echo "Reconnecting to $ORIGINAL_NETWORK..."

        if [ -n "$ORIGINAL_NETWORK_PASSWORD" ]; then
            /usr/sbin/networksetup -setairportnetwork "$WIFI_INTERFACE" "$ORIGINAL_NETWORK" "$ORIGINAL_NETWORK_PASSWORD" 2>&1
        else
            /usr/sbin/networksetup -setairportnetwork "$WIFI_INTERFACE" "$ORIGINAL_NETWORK" 2>&1
        fi

        sleep 8
        echo -e "${GREEN}Assumed reconnected to $ORIGINAL_NETWORK${NC}"
    fi
}

# Set up trap to always try to reconnect on exit or interrupt
trap 'emergency_reconnect; exit' EXIT INT TERM

# Helper functions
cycle_wifi_interface() {
    echo -e "${YELLOW}Cycling WiFi interface...${NC}"
    /usr/sbin/networksetup -setairportpower "$WIFI_INTERFACE" off
    sleep 2
    /usr/sbin/networksetup -setairportpower "$WIFI_INTERFACE" on
    sleep 3
    echo -e "${GREEN}WiFi interface cycled${NC}"
}

connect_to_network() {
    local network="$1"
    local password="$2"

    echo -e "${YELLOW}Connecting to $network...${NC}"
    echo "DEBUG: Attempting connection with interface: $WIFI_INTERFACE"

    local result
    if [ -z "$password" ]; then
        # Try without password (use keychain)
        echo "DEBUG: Connecting without password (using keychain)"
        result=$(/usr/sbin/networksetup -setairportnetwork "$WIFI_INTERFACE" "$network" 2>&1)
    else
        # Try with password
        echo "DEBUG: Connecting with password"
        result=$(/usr/sbin/networksetup -setairportnetwork "$WIFI_INTERFACE" "$network" "$password" 2>&1)
    fi

    local exit_code=$?
    echo "DEBUG: networksetup exit code: $exit_code"

    if [ -n "$result" ]; then
        echo "networksetup output: $result"
    fi

    if [ $exit_code -ne 0 ]; then
        echo -e "${RED}WARNING: networksetup returned error code $exit_code${NC}"
        echo "This may indicate a permissions issue or network not found"
    fi

    # Wait for connection to establish
    echo "Waiting ${CONNECTION_WAIT_TIME}s for connection to establish..."
    sleep $CONNECTION_WAIT_TIME
    echo -e "${GREEN}Assumed connected to $network${NC}"
    return 0
}

# Get current WiFi network
echo -e "${YELLOW}Getting current WiFi network...${NC}"

# Try multiple methods to get the SSID
ORIGINAL_NETWORK=$(/usr/sbin/networksetup -getairportnetwork "$WIFI_INTERFACE" 2>/dev/null | sed 's/Current Wi-Fi Network: //')

# If that didn't work, try the airport command
if [[ -z "$ORIGINAL_NETWORK" ]] || [[ "$ORIGINAL_NETWORK" == *"You are not associated"* ]]; then
    ORIGINAL_NETWORK=$(/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I 2>/dev/null | awk '/ SSID/ {print $2}')
fi

# Check if we got a network name
if [[ -z "$ORIGINAL_NETWORK" ]] || [[ "$ORIGINAL_NETWORK" == *"You are not associated"* ]]; then
    echo -e "${YELLOW}Could not auto-detect current WiFi network${NC}"
    echo -e "${YELLOW}Using fallback network: $ORIGINAL_NETWORK_FALLBACK${NC}"
    ORIGINAL_NETWORK="$ORIGINAL_NETWORK_FALLBACK"
fi

echo -e "${GREEN}Original network: $ORIGINAL_NETWORK${NC}"
echo "Safety: Auto-reconnect after ${EPAPER_TIMEOUT}s timeout or on any error/interrupt"

# Check if we're already on the Epaper network
if [ "$ORIGINAL_NETWORK" = "$EPAPER_NETWORK" ]; then
    echo -e "${YELLOW}Already connected to $EPAPER_NETWORK${NC}"
    echo "Skipping network switch..."
    SKIP_SWITCH=true
else
    SKIP_SWITCH=false
fi

# Switch to Epaper network
if [ "$SKIP_SWITCH" = false ]; then
    echo ""
    echo "======================================================"
    echo "Switching to E-Paper Network"
    echo "======================================================"

    connect_to_network "$EPAPER_NETWORK" "$EPAPER_NETWORK_PASSWORD"

    # Mark that we're now on E-Paper (for emergency reconnect)
    SWITCHED_TO_EPAPER=true

    # Start timeout watchdog in background
    echo "Starting ${EPAPER_TIMEOUT}s timeout watchdog..."
    (
        sleep "$EPAPER_TIMEOUT"
        echo ""
        echo "TIMEOUT: ${EPAPER_TIMEOUT}s elapsed on E-Paper network"
        echo "Forcing reconnection to original network..."
        # Send SIGTERM to parent script to trigger trap
        kill -TERM $$ 2>/dev/null
    ) &
    TIMEOUT_PID=$!
fi

# ============================================================
# DO YOUR WORK HERE
# ============================================================
echo ""
echo "======================================================"
echo "Uploading Files to E-Paper Device"
echo "======================================================"

# Run the upload script with unbuffered output (for real-time progress in GUI/TUI)
# Pass any command line arguments (file paths) to the upload script
if [ $# -gt 0 ]; then
    echo "DEBUG: Uploading specific files: $@"
    "$PYTHON" -u "$SCRIPT_DIR/upload_to_epaper.py" "$@"
else
    echo "DEBUG: Uploading all files"
    "$PYTHON" -u "$SCRIPT_DIR/upload_to_epaper.py"
fi

UPLOAD_RESULT=$?

if [ $UPLOAD_RESULT -eq 0 ]; then
    echo -e "${GREEN}File upload completed successfully${NC}"
else
    echo -e "${RED}File upload failed with exit code $UPLOAD_RESULT${NC}"
fi

# ============================================================
# END OF WORK SECTION
# ============================================================

# Kill timeout watchdog since we completed successfully
if [ -n "$TIMEOUT_PID" ] && ps -p "$TIMEOUT_PID" > /dev/null 2>&1; then
    kill "$TIMEOUT_PID" 2>/dev/null
    echo "Timeout watchdog cancelled"
fi

# Switch back to original network
if [ "$SKIP_SWITCH" = false ]; then
    echo ""
    echo "======================================================"
    echo "Switching Back to Original Network"
    echo "======================================================"

    connect_to_network "$ORIGINAL_NETWORK" "$ORIGINAL_NETWORK_PASSWORD"

    # Mark that we're safely back
    SWITCHED_TO_EPAPER=false

    # Disable the emergency reconnect trap since we're back safely
    trap - EXIT INT TERM
else
    echo -e "${YELLOW}Staying on $EPAPER_NETWORK (was already connected)${NC}"
fi

echo ""
echo "======================================================"
echo "Done!"
echo "======================================================"
