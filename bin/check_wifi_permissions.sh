#!/bin/bash
# Quick script to test WiFi permissions

echo "Testing WiFi control permissions..."
echo ""

# Test 1: Can we run networksetup?
echo "Test 1: Running networksetup..."
if /usr/sbin/networksetup -listallnetworkservices > /dev/null 2>&1; then
    echo "✓ networksetup command works"
else
    echo "✗ networksetup command failed"
    exit 1
fi

# Test 2: Can we get current WiFi network?
echo ""
echo "Test 2: Getting current WiFi network..."
CURRENT=$(/usr/sbin/networksetup -getairportnetwork en0 2>&1)
echo "Result: $CURRENT"

# Test 3: Check if we have WiFi control
echo ""
echo "Test 3: Checking WiFi control..."
if echo "$CURRENT" | grep -q "You are not associated"; then
    echo "✓ Not connected to WiFi (normal)"
elif echo "$CURRENT" | grep -q "Current Wi-Fi Network:"; then
    NETWORK=$(echo "$CURRENT" | sed 's/Current Wi-Fi Network: //')
    echo "✓ Connected to: $NETWORK"
else
    echo "⚠ Unexpected output: $CURRENT"
fi

echo ""
echo "If you see 'command not found' or permission errors above,"
echo "the GUI may not have permission to control WiFi."
echo ""
echo "To fix on macOS:"
echo "1. Go to System Preferences > Security & Privacy > Privacy"
echo "2. Select 'Automation' or 'Full Disk Access'"
echo "3. Grant permission to your terminal or Python"
echo ""
echo "Alternatively, you can:"
echo "- Run the GUI from Terminal.app (which has permissions)"
echo "- Use the 'Test Upload (no WiFi switch)' option instead"
