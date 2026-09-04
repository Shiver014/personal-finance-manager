#!/usr/bin/env python3
"""
build.py - Packages app.py into a single desktop executable with PyInstaller.

Run this script from the project root:
    python build.py

The finished executable will be placed in dist/FinanceTracker.exe on Windows
(or dist/FinanceTracker on macOS/Linux).

The SQLite database is intentionally NOT bundled into the executable. The
application creates/uses finance_data.db beside the executable so personal
financial data remains separate from the application binary.
"""
import os
import subprocess
import sys


def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    app = os.path.join(project_root, "app.py")

    if not os.path.exists(app):
        raise FileNotFoundError(f"Could not find application file: {app}")

    print("Installing/updating PyInstaller ...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "pyinstaller"
    ])

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "FinanceTracker",
        app,
    ]

    print("\nBuilding executable ...")
    subprocess.check_call(cmd, cwd=project_root)

    print("\nBuild complete.")
    print("Executable: dist/FinanceTracker")
    print("The runtime database will be created beside the executable on first launch.")


if __name__ == "__main__":
    main()
