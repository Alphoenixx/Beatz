import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil

print("\n=== Music Player Setup Script ===\n")



modules = [
    "python-vlc",
    "PyQt5",
    "mutagen",
    "requests",
    "beautifulsoup4",
]

print("Installing required Python modules...\n")

for m in modules:
    print(f"Installing {m} ...")
    subprocess.call([sys.executable, "-m", "pip", "install", m])




VLC_URL = "https://download.videolan.org/pub/videolan/vlc/3.0.20/win64/vlc-3.0.20-win64.zip"
VLC_ZIP = "vlc_portable.zip"
VLC_DIR = "vlc"

print("\nDownloading portable VLC (this may take a moment)...")

try:
    urllib.request.urlretrieve(VLC_URL, VLC_ZIP)
    print("VLC download complete.")
except Exception as e:
    print("VLC download failed:", e)
    sys.exit(1)

print("\nExtracting VLC...")
with zipfile.ZipFile(VLC_ZIP, "r") as zip_ref:
    zip_ref.extractall("vlc_tmp")


vlc_subfolder = None
for root, dirs, files in os.walk("vlc_tmp"):
    for d in dirs:
        if d.lower().startswith("vlc"):
            vlc_subfolder = os.path.join(root, d)
            break
    if vlc_subfolder:
        break

if vlc_subfolder is None:
    print("ERROR: VLC folder not found after extraction.")
    sys.exit(1)


if os.path.exists(VLC_DIR):
    shutil.rmtree(VLC_DIR)


shutil.move(vlc_subfolder, VLC_DIR)

# Cleanup
shutil.rmtree("vlc_tmp")
os.remove(VLC_ZIP)

print("VLC extracted successfully.")




PATCH_FILE = "vlc_loader_patch.py"

print("\nCreating VLC loader patch...")

with open(PATCH_FILE, "w") as f:
    f.write(r'''
import os, sys


vlc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vlc")
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(vlc_path)


os.environ["PYTHON_VLC_MODULE_PATH"] = vlc_path
os.environ["VLC_PLUGIN_PATH"] = os.path.join(vlc_path, "plugins")
''')

print("VLC loader patch created.")




print("\nPatching core.py to use local VLC...")

if not os.path.exists("core.py"):
    print("ERROR: core.py not found! Place this script next to your core.py.")
    sys.exit(1)

with open("core.py", "r", encoding="utf-8") as f:
    content = f.read()

if "vlc_loader_patch" not in content:
    print("Adding VLC loader patch import...")

    content = (
        "import vlc_loader_patch  # auto-load local VLC DLLs\n"
        + content
    )

    with open("core.py", "w", encoding="utf-8") as f:
        f.write(content)
else:
    print("core.py already patched.")


print("\n==== SETUP COMPLETE ====")
print("Your music player is now ready to run on this system.")
