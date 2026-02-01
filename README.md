# se-ml-football-predictor

## Download FIFA 23 dataset (via `uv`) ✅

This repo includes a helper script to download and unzip the FIFA 23 player dataset into `data/fifa23`.

Quick steps (recommended):

1. Install `uv` (one of):
   - macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - Or with pip: `pip install uv`

2. Run the downloader using `uv` (it will create an isolated environment and install the required deps automatically):

```bash
uv run scripts/download_fifa23.py
```

Notes:
- The script reads Kaggle credentials from your `.env` file (keys: `KAGGLE_USERNAME` and `KAGGLE_API_TOKEN`) and writes `~/.kaggle/kaggle.json` for the Kaggle CLI/SDK.
- The dataset is saved under `data/fifa23/` and this folder is ignored by git via `.gitignore`.
- To lock script dependencies for reproducibility you can run:

```bash
uv lock --script scripts/download_fifa23.py
```

If you prefer not to use `uv`, install dependencies manually and run the Python script:

```bash
python -m pip install kaggle python-dotenv
python scripts/download_fifa23.py
```
