# PyInstaller runtime hook for CloudDriveManager
import sys
import os
from pathlib import Path

if getattr(sys, "frozen", False):
    # sys._MEIPASS = temp extraction directory for onefile bundle
    meipass = sys._MEIPASS

    # Change working directory to the directory containing the executable
    bundle_dir = Path(sys.executable).parent
    os.chdir(bundle_dir)

    # Add meipass to path so bundled src/ is importable
    if meipass not in sys.path:
        sys.path.insert(0, meipass)

    # Also add bundle_dir for any non-bundled files
    if str(bundle_dir) not in sys.path:
        sys.path.insert(0, str(bundle_dir))
