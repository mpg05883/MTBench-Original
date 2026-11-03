# Setup

Run all commands from the repository root. This guide covers creating the uv
environment and downloading the published raw and processed MTBench datasets.

## 1. Set up the uv environment

On Linux or the Misha cluster, the setup script installs uv if needed and
creates `.venv/` using the project's Python version and dependency files:

```bash
./cli/utils/create_environment.sh
uv sync --all-extras
```

On Windows, install uv if it is not already available:

```powershell
winget install --id astral-sh.uv --exact
```

Open a new PowerShell window after installation, return to the repository
root, and create the environment with all dependencies:

```powershell
uv sync --all-extras
```

`uv sync` creates `.venv/` automatically. `--all-extras` includes the base
dependencies and every optional extra: `dev`, `weather`, `eval`, `model`, and
`download`. Python must satisfy `>=3.12,<3.14`; the repository's
`.python-version` selects the project version. PyTorch uses the CUDA 12.4
index configured in `pyproject.toml`.

For a smaller environment that only needs data downloads, use
`uv sync --extra download` instead. Keep `--all-extras` on later sync commands
if you want to retain all optional dependencies.

Use `uv run` to run Python inside the environment without activating it:

```bash
uv run python --version
```

Optionally create a `.env` file in the repository root for credentials. The
downloader loads it automatically. Set `HF_TOKEN` there if Hub authentication
is required; the datasets were publicly accessible without a token when
checked on 2026-11-01. Model API keys are not needed for downloads. Never
commit `.env`.

## 2. Download the data

Downloads come from Hugging Face and go into the repository's gitignored
`data/` directory. Each dataset group has a Bash launcher (with retries and
backoff) and a Python script that works in both PowerShell and Bash. The
Python scripts take no arguments.

### Processed data

Download the eight processed datasets (finance and weather aligned pairs and
QA sets, each with short and long settings) into `data/processed/`:

```bash
./cli/download/processed_mtbench.sh
```

or, from PowerShell:

```bash
uv run python scripts/download/processed_mtbench.py
```

### Raw data

Download finance news and stock series, plus weather reports and temperature
observations, into `data/raw/`:

```bash
./cli/download/raw_mtbench.sh
```

or, from PowerShell:

```bash
uv run python scripts/download/raw_mtbench.py
```

The finance stock dataset alone was about 16.5 GB when checked on 2026-11-01;
allow additional space for the other datasets and download cache. Treat
`data/raw/` as read-only after the download.

### Using the downloaded files

See [datasets.md](datasets.md) for the full dataset registry, exact folder
names, formats, and known limitations. Downloading processed datasets fetches
the authors' published files; it does not run local preprocessing.

Finance aligned pairs arrive as parquet tables. The finance evaluation
loaders need per-sample JSON files, so convert each setting you intend to use
into a separate output directory:

```bash
uv run python scripts/data/convert_finance_parquet.py --setting short --output-dir data/converted/finance/short
uv run python scripts/data/convert_finance_parquet.py --setting long --output-dir data/converted/finance/long
```

Pass the corresponding output directory to evaluation scripts through
`--dataset-folder`. Finance QA and the weather datasets already contain
per-sample JSON files.

The published raw Hub files currently lack ticker/station mappings and a
weather preprocessing step needed by the preparation scripts. Downloading
them is supported, but rebuilding the processed benchmark from them is not
yet reproducible. Use the published processed datasets to get started.
