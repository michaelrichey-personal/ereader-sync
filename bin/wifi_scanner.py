import sys
import time

import pywifi

target = "E-Paper"
pause = 1

wifi = pywifi.PyWiFi()
iface = wifi.interface()[0]

iface.scan()
time.sleep(pause)

if target not in iface.scan_results():
    print(f"{target} not found")
    sys.exit(1)

print(f"{target} found")
sys.exit(0)
