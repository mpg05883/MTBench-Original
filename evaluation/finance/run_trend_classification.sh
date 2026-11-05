#!/bin/bash
#SBATCH --job-name=fin_trend_classification
#SBATCH --partition=day
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=4G
#SBATCH --time=24:00:00
#SBATCH --output=slurm-%x-%j.out

# Submit from this script's directory (paths below are relative to it):
#   cd evaluation/finance && sbatch run_trend_classification.sh
# Run locally (e.g. Git Bash on Windows) with another model:
#   cd evaluation/finance && API_NAME=gpt-5.4-mini bash run_trend_classification.sh
# Smoke test on the first 3 samples:
#   cd evaluation/finance && API_NAME=gpt-5.4-mini bash run_trend_classification.sh 3
# Time-series-only inputs (no news text in the prompt):
#   cd evaluation/finance && MODE=timeseries_only bash run_trend_classification.sh

# Cluster-only setup; skipped where `module` or `conda` is not available.
if command -v module >/dev/null 2>&1; then
    module load miniconda
fi
if command -v conda >/dev/null 2>&1; then
    eval "$(conda shell.bash hook)"
else
    # Non-interactive bash (e.g. Git Bash on Windows) does not define `conda`;
    # load it from the install. Set CONDA_ROOT if conda lives elsewhere.
    for root in "${CONDA_ROOT:-}" "$HOME/anaconda3" "$HOME/miniconda3"; do
        if [ -n "$root" ] && [ -f "$root/etc/profile.d/conda.sh" ]; then
            . "$root/etc/profile.d/conda.sh"
            break
        fi
    done
fi
if ! command -v conda >/dev/null 2>&1; then
    echo "conda not found; set CONDA_ROOT to your conda install" >&2; exit 1
fi
conda activate MTBench || { echo "conda env 'MTBench' not found" >&2; exit 1; }
# On Windows, conda's openssl activate script for bash points SSL_CERT_FILE
# at <env>/ssl/cacert.pem, but the file is in <env>/Library/ssl/. A missing
# file makes every API call fail with "[Errno 2] No such file or directory".
if [ -n "${SSL_CERT_FILE:-}" ] && [ ! -f "$SSL_CERT_FILE" ]; then
    if [ -f "$CONDA_PREFIX/Library/ssl/cacert.pem" ]; then
        export SSL_CERT_FILE="$CONDA_PREFIX/Library/ssl/cacert.pem"
    else
        unset SSL_CERT_FILE
    fi
fi

cd "${SLURM_SUBMIT_DIR:-$(dirname "$0")}"

# Generate lists first with evaluation/run_make_parity_subsets.sh.
# Override SUBSETS_DIR to use a custom --output-dir (relative to this directory).
SUBSETS_DIR="${SUBSETS_DIR:-../../subsets}"

# Select from ["gpt-5.1", "gpt-5.4-mini", ...]; each Azure model needs its
# deployment env var in .env (see AZURE_DEPLOYMENT_ENV in evaluation/api_call.py).
API_NAME="${API_NAME:-gpt-5.1}"
# Set BATCH_FLAGS="--batch --wait" to use the Batch API (see evaluation/batch.py).
BATCH_FLAGS="${BATCH_FLAGS:-}"
MODE="${MODE:-combined}" # select from ["timeseries_only", "text_only", "combined"]
case "$MODE" in
    timeseries_only|text_only|combined) ;;
    *) echo "Invalid MODE: $MODE" >&2; exit 1 ;;
esac
SETTING="${SETTING:-long}" # select from ["short", "long"]
case "$SETTING" in
    short) IN_DAYS=7; OUT_DAYS=1 ;;
    long) IN_DAYS=30; OUT_DAYS=7 ;;
    *) echo "Invalid SETTING: $SETTING" >&2; exit 1 ;;
esac
# Use the same converted folder passed to make_parity_subsets.py.
CONVERTED_DIR="${CONVERTED_DIR:-../../data/processed/finance_converted}"

# Smoke test: evaluate only the first N samples, given as the first argument
# or as LIMIT (e.g. `bash run_trend_classification.sh 3`). Results then go to a
# separate `_limitN` folder so they never mix with a full run.
LIMIT="${1:-${LIMIT:-}}"
SAVE_PATH="../../results/finance/trend_classification_in${IN_DAYS}_out${OUT_DAYS}/${API_NAME}/${MODE}"
LIMIT_FLAGS=""
if [ -n "$LIMIT" ]; then
    case "$LIMIT" in
        ''|*[!0-9]*) echo "Invalid LIMIT: $LIMIT (must be a positive integer)" >&2; exit 1 ;;
    esac
    LIMIT_FLAGS="--limit=$LIMIT"
    SAVE_PATH="${SAVE_PATH}_limit${LIMIT}"
fi

python trend_classification.py \
    --subset_file="${SUBSETS_DIR}/finance_trend_${SETTING}.json" \
    --dataset_folder="${CONVERTED_DIR}/${SETTING}" \
    --save_path="$SAVE_PATH" \
    --model=$API_NAME $BATCH_FLAGS $LIMIT_FLAGS \
    --mode=$MODE
