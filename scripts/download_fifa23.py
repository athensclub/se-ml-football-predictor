#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "kaggle",
#   "python-dotenv",
# ]
# ///

"""Download and unzip the FIFA 23 dataset into data/fifa23 using Kaggle credentials from .env.

Usage:
  - Install `uv` (see https://docs.astral.sh/uv/getting-started/installation/)
  - Run: `uv run scripts/download_fifa23.py`

If you don't use `uv`, you can install dependencies with `python -m pip install kaggle python-dotenv`
and run `python scripts/download_fifa23.py`.

The script will write a `~/.kaggle/kaggle.json` file from env vars `KAGGLE_USERNAME` and `KAGGLE_API_TOKEN`.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except Exception:
    DOTENV_AVAILABLE = False


def read_env(env_path: Path):
    if DOTENV_AVAILABLE:
        load_dotenv(dotenv_path=str(env_path))
    # Values from environment variables (or .env if loaded)
    username = os.getenv("KAGGLE_USERNAME")
    key = os.getenv("KAGGLE_API_TOKEN") or os.getenv("KAGGLE_KEY")
    return username, key


def write_kaggle_json(username: str, key: str):
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(mode=0o700, exist_ok=True)
    kaggle_json = kaggle_dir / "kaggle.json"
    with kaggle_json.open("w", encoding="utf-8") as f:
        json.dump({"username": username, "key": key}, f)
    try:
        kaggle_json.chmod(0o600)
    except Exception:
        # Windows may not support chmod the same way; ignore errors
        pass
    return kaggle_json


def download_with_kaggle_api(dest_dir: Path):
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except Exception as e:
        raise RuntimeError("Kaggle package not available: %s" % e)
    api = KaggleApi()
    api.authenticate()
    print("Downloading via Kaggle API (this may take a while)...")
    api.dataset_download_files(
        "stefanoleone992/fifa-23-complete-player-dataset",
        path=str(dest_dir), unzip=True,
    )


def download_with_cli(dest_dir: Path):
    cmd = [
        "kaggle",
        "datasets",
        "download",
        "-d",
        "stefanoleone992/fifa-23-complete-player-dataset",
        "-p",
        str(dest_dir),
        "--unzip",
    ]
    print("Falling back to kaggle CLI:", " ".join(cmd))
    subprocess.check_call(cmd)


def main():
    env_path = Path(__file__).resolve().parents[1] / ".env"
    username, key = read_env(env_path)
    if not username or not key:
        print(
            "Missing KAGGLE_USERNAME or KAGGLE_API_TOKEN in environment or .env.\nPlease add them or run: `uv add python-dotenv` and put them in a .env file.`,",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Using KAGGLE_USERNAME=", username)
    kaggle_json = write_kaggle_json(username, key)
    print(f"Wrote kaggle credentials to {kaggle_json}")

    dest_dir = Path("data") / "fifa23"
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Try Kaggle API first (preferred)
    try:
        download_with_kaggle_api(dest_dir)
    except Exception as e:
        print("Kaggle API download failed (will try CLI). Error:", e, file=sys.stderr)
        try:
            download_with_cli(dest_dir)
        except Exception as e2:
            print("kaggle CLI also failed. Error:", e2, file=sys.stderr)
            print("Ensure `uv add kaggle python-dotenv` has been run and you have network access.")
            sys.exit(1)

    print("Download complete. Files in:", dest_dir)


if __name__ == "__main__":
    main()
