#!/bin/bash
#SBATCH --job-name=convert_finance_parquet
#SBATCH --partition=day
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=4G
#SBATCH --time=01:00:00
#SBATCH --output=slurm-%x-%j.out

# Run from the repository root:
#   sbatch evaluation/run_convert_finance_parquet.sh
#   bash evaluation/run_convert_finance_parquet.sh --max-rows 10
# Override DATA_DIR or CONVERTED_DIR for custom input/output locations.
# Use the same CONVERTED_DIR for parity subset generation and evaluation.
set -euo pipefail

module load miniconda
eval "$(conda shell.bash hook)"
conda activate MTBench

cd "${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

DATA_DIR="${DATA_DIR:-./data/processed/finance}"
CONVERTED_DIR="${CONVERTED_DIR:-./data/processed/finance_converted}"

for setting in short long; do
    case "$setting" in
        short) IN_DAYS=7; OUT_DAYS=1 ;;
        long) IN_DAYS=30; OUT_DAYS=7 ;;
    esac
    python evaluation/convert_finance_parquet.py \
        "${DATA_DIR}/aligned_in${IN_DAYS}days_out${OUT_DAYS}days" \
        --output-dir "${CONVERTED_DIR}/${setting}" \
        "$@"
done
