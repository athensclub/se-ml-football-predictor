#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Download and extract the StatsBomb open-data repository into data/statsbomb-opendata.

Usage:
  python scripts/download_statsbomb.py
  or with uv: `uv run scripts/download_statsbomb.py`
"""
from pathlib import Path
import sys
import shutil
import zipfile
import urllib.request
import tempfile

GITHUB_ZIP = "https://github.com/statsbomb/open-data/archive/refs/heads/master.zip"
DEST = Path("data") / "statsbom-opendata"


def download_zip(url: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} -> {target}")
    urllib.request.urlretrieve(url, str(target))
    print("Download complete")
    return target


def extract_zip(zip_path: Path, dest_dir: Path):
    print(f"Extracting {zip_path} -> {dest_dir}")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(dest_dir)
    print("Extraction complete")


def move_extracted_contents(extracted_root: Path, dest: Path):
    # extracted_root is likely extracted_root / 'open-data-master'
    if not extracted_root.exists():
        raise FileNotFoundError(extracted_root)
    # Content may include folders like 'data', 'docs', etc.
    print(f"Moving contents from {extracted_root} -> {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    for child in extracted_root.iterdir():
        target = dest / child.name
        if target.exists():
            # If target exists, remove it first to avoid conflicts
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        if child.is_dir():
            shutil.move(str(child), str(target))
        else:
            shutil.move(str(child), str(target))
    print("Move complete")


def main():
    tmpdir = Path(tempfile.mkdtemp(prefix="statsbomb_"))
    zip_path = tmpdir / "open-data-master.zip"
    try:
        download_zip(GITHUB_ZIP, zip_path)
        extract_zip(zip_path, tmpdir)
        extracted_root = tmpdir / "open-data-master"
        if not extracted_root.exists():
            print("Unexpected archive layout: 'open-data-master' folder missing", file=sys.stderr)
            sys.exit(1)
        move_extracted_contents(extracted_root, DEST)
    finally:
        # Clean up temp dir
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
    print(f"StatsBomb open-data is available in {DEST}")


if __name__ == '__main__':
    main()
