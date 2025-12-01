import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil

def install_packages(packages):
    print("\nInstalling required Python packages...\n")
    for pkg in packages:
        print(f"Installing {pkg}...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", pkg], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERROR: Failed to install {pkg}.\n{result.stderr}")
            sys.exit(1)
    print("All Python packages installed successfully.\n")

def download_and_extract_vlc(url, zip_name, extract_folder, target_folder):
    print(f"Downloading VLC from {url} ... This may take a while.")
    try:
        urllib.request.urlretrieve(url, zip_name)
        print("VLC download complete.")
    except Exception as e:
        print(f"ERROR: Failed to download VLC: {e}")
        sys.exit(1)

    print(f"Extracting VLC to '{extract_folder}' ...")
    try:
        with zipfile.ZipFile(zip_name, "r") as zip_ref:
            zip_ref.extractall(extract_folder)
    except Exception as e:
        print(f"ERROR: Failed to extract VLC zip: {e}")
        sys.exit(1)

    vlc_subfolder = None
    for root, dirs, files in os.walk(extract_folder):
        for d in dirs:
            if d.lower().startswith("vlc"):
                vlc_subfolder = os.path.join(root, d)
                break
        if vlc_subfolder:
            break

    if vlc_subfolder is None:
        print("ERROR: VLC folder not found after extraction.")
        sys.exit(1)

    if os.path.exists(target_folder):
        try:
            shutil.rmtree(target_folder)
        except Exception as e:
            print(f"ERROR: Failed to remove existing VLC folder: {e}")
            sys.exit(1)

    try:
        shutil.move(vlc_subfolder, target_folder)
    except Exception as e:
        print(f"ERROR: Failed to move VLC folder: {e}")
        sys.exit(1)

    # Clean up temporary extraction folder and zip
    try:
        shutil.rmtree(extract_folder)
        os.remove(zip_name)
    except Exception as e:
        print(f"WARNING: Failed to clean up temporary files: {e}")

    print("VLC extracted and set up successfully.\n")

def create_vlc_loader_patch(patch_filename, vlc_foldername):
    patch_code = f'''import os

vlc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "{vlc_foldername}")
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(vlc_path)

os.environ["PYTHON_VLC_MODULE_PATH"] = vlc_path
os.environ["VLC_PLUGIN_PATH"] = os.path.join(vlc_path, "plugins")
'''
    try:
        with open(patch_filename, "w", encoding="utf-8") as f:
            f.write(patch_code)
    except Exception as e:
        print(f"ERROR: Failed to write VLC loader patch file: {e}")
        sys.exit(1)
    print(f"Created VLC loader patch file '{patch_filename}'.\n")

def patch_main_file(main_file, patch_import_line):
    if not os.path.exists(main_file):
        print(f"ERROR: {main_file} not found in current directory. Please run this script in your project root.")
        sys.exit(1)

    try:
        with open(main_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"ERROR: Failed to read {main_file}: {e}")
        sys.exit(1)

    if patch_import_line in content:
        print(f"{main_file} already patched.")
        return

    try:
        with open(main_file, "w", encoding="utf-8") as f:
            f.write(patch_import_line + "\n" + content)
    except Exception as e:
        print(f"ERROR: Failed to patch {main_file}: {e}")
        sys.exit(1)

    print(f"Patched {main_file} to import VLC loader patch.\n")

def main():
    print("\n=== Music Player Full Setup Script ===\n")

    required_packages = [
        "python-vlc",
        "PyQt5",
        "mutagen",
        "requests",
        "beautifulsoup4",
        "qtawesome",
        "qdarkstyle"
    ]

    install_packages(required_packages)

    vlc_download_url = "https://download.videolan.org/pub/videolan/vlc/3.0.20/win64/vlc-3.0.20-win64.zip"
    vlc_zip = "vlc_portable.zip"
    vlc_tmp_extract = "vlc_tmp"
    vlc_folder = "vlc"
    patch_file = "vlc_loader_patch.py"
    main_py_file = "main.py"
    patch_import_line = "import vlc_loader_patch  # auto-load local VLC DLLs"

    download_and_extract_vlc(vlc_download_url, vlc_zip, vlc_tmp_extract, vlc_folder)
    create_vlc_loader_patch(patch_file, vlc_folder)
    patch_main_file(main_py_file, patch_import_line)

    print("=== Setup complete! You can now run your music player application. ===\n")

if __name__ == "__main__":
    main()
