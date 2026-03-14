#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
from pathlib import Path

def build():
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)

    print(f"Starting build on {sys.platform}...")

    # 1. Install requirements
    print("Installing requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "build-requirements.txt"], check=True)

    # 2. Clean previous builds
    print("Cleaning old build files...")
    for folder in ["build", "dist"]:
        if (project_root / folder).exists():
            shutil.rmtree(project_root / folder)

    # 3. Run PyInstaller
    print("Running PyInstaller...")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "MailBot.spec"], check=True)

    # 4. Post-build tasks (macOS only)
    if sys.platform == "darwin":
        app_path = project_root / "dist" / "Mail Bot.app"
        if app_path.exists():
            print("Cleaning macOS attributes and re-signing...")
            subprocess.run(["xattr", "-cr", str(app_path)], check=True)
            subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app_path)], check=True)
            print(f"App built at: {app_path}")

    print("Build complete!")

if __name__ == "__main__":
    try:
        build()
    except Exception as e:
        print(f"Build failed: {e}")
        sys.exit(1)
