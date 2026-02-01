#!/usr/bin/env python3
"""Extract the FIFA23 dataset zip in data/fifa23 and remove the zip file.

Usage: python scripts/extract_fifa23.py
"""
from pathlib import Path
import zipfile
import sys

zip_path = Path("data") / "fifa23" / "fifa-23-complete-player-dataset.zip"
if not zip_path.exists():
    print(f"ZIP file not found: {zip_path}")
    sys.exit(1)

dest = zip_path.parent
print(f"Extracting {zip_path} -> {dest}")
with zipfile.ZipFile(zip_path, 'r') as z:
    z.extractall(dest)
    namelist = z.namelist()

print(f"Extracted {len(namelist)} entries. Sample: {namelist[:5]}")
# Remove the zip file
try:
    zip_path.unlink()
    print(f"Removed zip file: {zip_path}")
except Exception as e:
    print(f"Failed to remove zip: {e}")
    sys.exit(1)

print("Done.")
