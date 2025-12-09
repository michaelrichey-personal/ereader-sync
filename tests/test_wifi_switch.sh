#!/bin/bash
# Simple test script to debug WiFi switching from GUI

echo "=== WiFi Switch Test Script ==="
echo "START TIME: $(date)"
echo "USER: $(whoami)"
echo "PWD: $(pwd)"
echo "SHELL: $SHELL"
echo ""

# Test 1: Can we find networksetup?
echo "Test 1: Looking for networksetup..."
if command -v networksetup &> /dev/null; then
    echo "✓ networksetup found at: $(which networksetup)"
else
    echo "✗ networksetup NOT FOUND in PATH"
    echo "PATH: $PATH"
    exit 1
fi

# Test 2: Can we read config files?
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$REPO_ROOT/config"

echo ""
echo "Test 2: Config files..."
echo "Config dir: $CONFIG_DIR"
if [ -f "$CONFIG_DIR/application.config" ]; then
    echo "✓ application.config exists"
else
    echo "✗ application.config NOT FOUND"
    exit 1
fi

if [ -f "$CONFIG_DIR/secrets.config" ]; then
    echo "✓ secrets.config exists"
else
    echo "✗ secrets.config NOT FOUND"
    exit 1
fi

# Test 3: Can we source the configs?
echo ""
echo "Test 3: Loading configs..."
set -a
source "$CONFIG_DIR/application.config"
source "$CONFIG_DIR/secrets.config"
set +a

echo "EPAPER_NETWORK: $EPAPER_NETWORK"
echo "WIFI_INTERFACE: $WIFI_INTERFACE"
echo "EPAPER_NETWORK_PASSWORD: ${EPAPER_NETWORK_PASSWORD:0:3}***"

# Test 4: Can we get current network?
echo ""
echo "Test 4: Getting current WiFi network..."
CURRENT=$(/usr/sbin/networksetup -getairportnetwork "$WIFI_INTERFACE" 2>&1)
echo "networksetup returned: $?"
echo "Output: $CURRENT"

# Test 5: Try to switch networks
echo ""
echo "Test 5: Attempting to switch to $EPAPER_NETWORK..."
echo "Command: /usr/sbin/networksetup -setairportnetwork $WIFI_INTERFACE $EPAPER_NETWORK [password]"

OUTPUT=$(/usr/sbin/networksetup -setairportnetwork "$WIFI_INTERFACE" "$EPAPER_NETWORK" "$EPAPER_NETWORK_PASSWORD" 2>&1)
EXIT_CODE=$?

echo "Exit code: $EXIT_CODE"
echo "Output: $OUTPUT"

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Network switch command succeeded"
    echo ""
    echo "Waiting 5 seconds..."
    sleep 5

    # Check if we actually switched
    NEW_NETWORK=$(/usr/sbin/networksetup -getairportnetwork "$WIFI_INTERFACE" 2>&1)
    echo "Current network: $NEW_NETWORK"

    if echo "$NEW_NETWORK" | grep -q "$EPAPER_NETWORK"; then
        echo "✓ Successfully switched to $EPAPER_NETWORK"
    else
        echo "⚠ Network switch command succeeded but still on: $NEW_NETWORK"
    fi
else
    echo "✗ Network switch command FAILED"
    echo "This indicates a permissions or network issue"
fi

echo ""
echo "END TIME: $(date)"
echo "=== Test Complete ==="
