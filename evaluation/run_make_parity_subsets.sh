#!/bin/bash
#SBATCH --job-name=make_parity_subsets
#SBATCH --partition=day
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=4G
#SBATCH --time=01:00:00
#SBATCH --output=slurm-%x-%j.out

# Draw the fixed 300-item subsets of the refactor evaluation parity experiment
# with evaluation/make_parity_subsets.py. Writes subsets/<cell>.json and
# manifest.json in the repository root (unless --output-dir is given).
#
# Convert the finance pairs first with evaluation/run_convert_finance_parquet.sh,
# and use the same converted folder in the refactored repository.
#
# Run from the repository root (extra flags are passed to the script):
#   sbatch evaluation/run_make_parity_subsets.sh --dry-run
#   sbatch evaluation/run_make_parity_subsets.sh
#   bash evaluation/run_make_parity_subsets.sh --finance-converted-dir <dir>
#
# Flags: --finance-converted-dir <dir> (default: data/processed/
#   finance_converted), plus --dry-run, --seed, --size, --min-per-label,
#   --max-group-share, --data-dir and --output-dir.

module load miniconda
eval "$(conda shell.bash hook)"
conda activate MTBench

cd "${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

CONVERTED_DIR="./data/processed/finance_converted"

# A --finance-converted-dir given on the command line comes later and wins.
python evaluation/make_parity_subsets.py \
    --finance-converted-dir "$CONVERTED_DIR" \
    "$@"
