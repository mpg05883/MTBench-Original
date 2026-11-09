#!/bin/bash
#SBATCH --job-name=wea_temperature_forecast
#SBATCH --partition=day
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=4G
#SBATCH --time=24:00:00
#SBATCH --output=slurm-%x-%j.out

# Submit from this script's directory (paths below are relative to it):
#   cd evaluation/weather && sbatch run_temperature_forecast.sh
# Run locally (e.g. Git Bash on Windows), with options from the environment
# (see evaluation/setup_env.sh); the optional argument limits the samples:
#   cd evaluation/weather && API_NAME=gpt-5.4-mini MODE=timeseries_only bash run_temperature_forecast.sh 3

cd "${SLURM_SUBMIT_DIR:-$(dirname "$0")}"
ALLOWED_MODES="timeseries_only text_only combined"
. ../setup_env.sh

# Generate lists first with evaluation/run_make_parity_subsets.sh.
# Override SUBSETS_DIR to use a custom --output-dir (relative to this directory).
SUBSETS_DIR="${SUBSETS_DIR:-../../subsets}"

SETTING="${SETTING:-short}" # select from ["short", "long"]
case "$SETTING" in
    short) IN_DAYS=7; OUT_DAYS=1 ;;
    long) IN_DAYS=14; OUT_DAYS=3 ;;
    *) echo "Invalid SETTING: $SETTING" >&2; exit 1 ;;
esac

# timeseries forecasting
python temperature_forecast.py \
    --subset_file="${SUBSETS_DIR}/weather_forecast_${SETTING}.json" \
    --dataset_folder="../../data/processed/weather/aligned_in${IN_DAYS}days_out${OUT_DAYS}days" \
    --save_path="../../results/weather/temperature_forecast_in${IN_DAYS}_out${OUT_DAYS}/${API_NAME}/${MODE}${LIMIT_SUFFIX}" \
    --model=$API_NAME $BATCH_FLAGS $LIMIT_FLAGS \
    --mode=$MODE \
    --in_days=$IN_DAYS \
    --out_days=$OUT_DAYS
