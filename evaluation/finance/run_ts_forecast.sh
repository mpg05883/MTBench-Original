#!/bin/bash
#SBATCH --job-name=fin_ts_forecast
#SBATCH --partition=day
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=4G
#SBATCH --time=24:00:00
#SBATCH --output=slurm-%x-%j.out

# Submit from this script's directory (paths below are relative to it):
#   cd evaluation/finance && sbatch run_ts_forecast.sh
# Run locally (e.g. Git Bash on Windows), with options from the environment
# (see evaluation/setup_env.sh); the optional argument limits the samples:
#   cd evaluation/finance && API_NAME=gpt-5.4-mini MODE=timeseries_only bash run_ts_forecast.sh 3

cd "${SLURM_SUBMIT_DIR:-$(dirname "$0")}"
ALLOWED_MODES="timeseries_only text_only combined"
. ../setup_env.sh

# Generate lists first with evaluation/run_make_parity_subsets.sh.
# Override SUBSETS_DIR to use a custom --output-dir (relative to this directory).
SUBSETS_DIR="${SUBSETS_DIR:-../../subsets}"

INDICATOR_TYPE="time" # select from ["macd", "bb", "time"]
SETTING="${SETTING:-long}" # select from ["short", "long"]
case "$SETTING" in
    short) IN_DAYS=7; OUT_DAYS=1 ;;
    long) IN_DAYS=30; OUT_DAYS=7 ;;
    *) echo "Invalid SETTING: $SETTING" >&2; exit 1 ;;
esac
# Use the same converted folder passed to make_parity_subsets.py.
CONVERTED_DIR="${CONVERTED_DIR:-../../data/processed/finance_converted}"
# timeseries forecasting
python value_prediction.py \
    --subset_file="${SUBSETS_DIR}/finance_forecast_${INDICATOR_TYPE}_${SETTING}.json" \
    --dataset_folder="${CONVERTED_DIR}/${SETTING}" \
    --save_path="../../results/finance/pred_${INDICATOR_TYPE}_in${IN_DAYS}_out${OUT_DAYS}/${API_NAME}/${MODE}${LIMIT_SUFFIX}" \
    --indicator=$INDICATOR_TYPE \
    --model=$API_NAME $BATCH_FLAGS $LIMIT_FLAGS \
    --mode=$MODE
