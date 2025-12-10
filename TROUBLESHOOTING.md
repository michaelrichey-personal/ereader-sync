# Troubleshooting Guide

## GUI/TUI WiFi Sync Issues

If the sync feature isn't working in the GUI/TUI, follow these steps:

### macOS Permissions Issue (MOST COMMON)

GUI apps on macOS need special permissions to control WiFi. If switching works from command line but not from GUI:

**Step 1: Use the GUI Test Button**
1. Launch GUI: `python3 bin/gui.py` (from terminal)
2. Go to Sync tab
3. Click **"Test WiFi Switch"** button
4. Watch the detailed output - it will show you exactly what's failing

The test output will tell you if it's a permissions issue, config issue, or something else.

**Step 2: Solutions Based on Test Results**

**If test shows permission errors:**
- Option A: Always run GUI from Terminal: `python3 bin/gui.py`
- Option B: Grant Full Disk Access to Terminal/Python in System Preferences > Security & Privacy

**If test shows config not found:**
- Check that `config/application.config` and `config/secrets.config` exist
- Make sure you're running from the correct directory

**If test shows networksetup errors:**
- Network might not be in range
- Password might be incorrect in `config/secrets.config`
- WiFi interface name might be wrong (check `WIFI_INTERFACE` in config)
- Error -3900 ("Failed to join network"): Usually indicates authentication failure or network not available

**Option: Skip WiFi Switching Entirely**
- Manually connect to E-Paper WiFi first
- In GUI, click "Test Upload (no WiFi)" button
- This bypasses WiFi automation

**Command Line Tests:**
```bash
# Test 1: Check permissions
./bin/check_wifi_permissions.sh

# Test 2: Test WiFi switching
./bin/test_wifi_switch.sh

# Test 3: Full sync from command line
./bin/switch_to_epaper_wifi.sh
```

### Step 1: Test Direct Upload First

1. **Manually connect to your E-Paper WiFi network**
2. In the GUI/TUI Sync tab, **uncheck** "Auto-switch WiFi network"
3. Click "Test Upload (no WiFi switch)" button (GUI only) or use unchecked sync (TUI)
4. Check the output for errors

**If this fails:** The issue is with the upload script or device connectivity
**If this works:** The issue is with WiFi switching

### Step 2: Test WiFi Switching from Command Line

Open a terminal and run:
```bash
./bin/switch_to_epaper_wifi.sh
```

Watch for errors. Common issues:

#### Error: "networksetup: command not found"
- This is a macOS-specific tool
- If on Linux, you'll need to modify the script for your system

#### Error: "Permission denied" or similar
- WiFi control requires admin permissions on some systems
- Try running: `sudo ./bin/switch_to_epaper_wifi.sh`

#### Script hangs or times out
- Check your config values in `config/application.config`:
  - `CONNECTION_WAIT_TIME` (default: 8 seconds)
- Try increasing this value

### Step 3: Verify Configuration

Check `config/secrets.config`:
```bash
cat config/secrets.config
```

Verify:
- `EPAPER_NETWORK_PASSWORD` is correct
- `ORIGINAL_NETWORK_PASSWORD` is correct (for returning to your network)

Check `config/application.config`:
```bash
cat config/application.config
```

Verify:
- `EPAPER_NETWORK` matches your e-paper device's WiFi name exactly
- `EPAPER_DEVICE_IP` is correct (default: 192.168.3.3)
- `WIFI_INTERFACE` is correct (default: en0 for macOS)

### Step 4: Check Device Connectivity

When connected to E-Paper WiFi, test:
```bash
ping 192.168.3.3
```

If ping fails:
- Check device is powered on
- Verify correct WiFi network
- Check device IP address (may not be 192.168.3.3)

### Step 5: Test Upload Manually

When connected to E-Paper WiFi:
```bash
python3 bin/upload_to_epaper.py
```

This will show detailed error messages if upload fails.

## GUI-Specific Issues

### No Output When Clicking Buttons

If buttons don't seem to do anything:
1. Check terminal where you launched the GUI for Python errors
2. Verify scripts exist:
   ```bash
   ls -l bin/scrape_*.py bin/upload_*.py bin/switch_*.sh
   ```

### Output Text Doesn't Update

This was a known issue with threading - make sure you're using the latest version of `bin/gui.py` which uses `Clock.schedule_once()`.

## TUI-Specific Issues

### Keyboard Not Working

- Make sure terminal has focus
- Try pressing `q` to quit, then restart

### Display Issues

- Resize terminal window (minimum 80x24 recommended)
- Try a different terminal emulator

## Common Errors

### "Config file not found"

```bash
# Create from template
cp config/secrets.config.template config/secrets.config

# Edit your passwords
nano config/secrets.config
```

### "No EPUB files found"

Generate content first:
```bash
python3 bin/scrape_hcr_to_epub.py
python3 bin/scrape_hn_to_epub.py
```

Or use the Generate tab in GUI/TUI.

### "Connection timeout" or "Failed to connect"

1. Verify e-paper device is on E-Paper WiFi
2. Check device IP with: `arp -a` while connected to E-Paper network
3. Update `EPAPER_DEVICE_IP` in config if different
4. Try accessing device web interface in browser: `http://192.168.3.3`

## Getting Help

If issues persist:
1. Run commands from terminal to see full error messages
2. Check device documentation for correct IP and upload endpoint
3. Verify all config values are correct
4. Try running scripts individually to isolate the problem
