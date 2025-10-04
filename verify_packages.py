import sys

print(f"Python Executable: {sys.executable}")

try:
    import pyotp
    print(f"[SUCCESS] 'pyotp' is installed at: {pyotp.__file__}")
except ImportError:
    print("[ERROR] 'pyotp' is NOT installed.")

try:
    import qrcode
    print(f"[SUCCESS] 'qrcode' is installed at: {qrcode.__file__}")
except ImportError:
    print("[ERROR] 'qrcode' is NOT installed.")
