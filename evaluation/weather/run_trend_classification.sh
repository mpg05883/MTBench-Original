#!/bin/bash
#SBATCH --job-name=wea_trend_classification
#SBATCH --partition=day
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=4G
#SBATCH --time=24:00:00
#SBATCH --output=slurm-%x-%j.out

# Submit from this script's directory (paths below are relative to it):
#   cd evaluation/weather && sbatch run_trend_classification.sh

module load miniconda
eval "$(conda shell.bash hook)"
conda activate MTBench

cd "${SLURM_SUBMIT_DIR:-$(dirname "$0")}"

# Generate lists first with evaluation/run_make_parity_subsets.sh.
# Override SUBSETS_DIR to use a custom --output-dir (relative to this directory).
SUBSETS_DIR="${SUBSETS_DIR:-../../subsets}"

API_NAME="gpt-5.1"
MODE="combined" # select from ["timeseries_only", "combined"]
PAST_FUTURE="past" # select from ["past", "future"]

SETTING="${SETTING:-short}" # select from ["short", "long"]
case "$SETTING" in
    short) IN_DAYS=7; OUT_DAYS=1 ;;
    long) IN_DAYS=14; OUT_DAYS=3 ;;
    *) echo "Invalid SETTING: $SETTING" >&2; exit 1 ;;
esac

python trend_classification.py \
    --subset_file="${SUBSETS_DIR}/weather_trend_${PAST_FUTURE}_${SETTING}.json" \
    --dataset_folder="../../data/processed/weather/aligned_in${IN_DAYS}days_out${OUT_DAYS}days" \
    --save_path="../../results/weather/trend_classification_in${IN_DAYS}_out${OUT_DAYS}/${API_NAME}/${MODE}" \
    --model=$API_NAME \
    --mode=$MODE \
    --in_days=$IN_DAYS \
    --out_days=$OUT_DAYS \
    --past_future=$PAST_FUTURE