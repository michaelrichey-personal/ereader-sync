#!/usr/bin/env python3
"""Test script to verify requests module is available."""
import sys
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")

try:
    import requests
    print("✓ SUCCESS: requests module found")
    print(f"  requests location: {requests.__file__}")
except ImportError as e:
    print(f"✗ FAILURE: {e}")
    sys.exit(1)
