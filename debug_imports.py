
import sys, os
import traceback

print("--- Python Info ---")
print(sys.executable)
print(sys.version)

print("\n--- Sys Path ---")
# Apply the same logic as main.py
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir in sys.path:
    sys.path.remove(script_dir)

venv_site = os.path.join(script_dir, '.venv', 'lib', 'python3.13', 'site-packages')
if os.path.isdir(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)
    
print(sys.path)

print("\n--- Attempting Imports ---")
try:
    import objc
    print(f"objc: {objc.__file__}")
except ImportError:
    print("Failed to import objc")
    traceback.print_exc()

try:
    import Quartz
    print(f"Quartz: {Quartz.__file__}")
except ImportError:
    print("Failed to import Quartz")
    traceback.print_exc()

try:
    import AppKit
    print(f"AppKit: {AppKit.__file__}")
except ImportError:
    print("Failed to import AppKit")
    traceback.print_exc()

try:
    import CoreGraphics
    print(f"CoreGraphics: {CoreGraphics.__file__}")
except ImportError:
    print("Failed to import CoreGraphics")
    traceback.print_exc()
