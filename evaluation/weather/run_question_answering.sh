#!/bin/bash
#SBATCH --job-name=wea_question_answering
#SBATCH --partition=day
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=4G
#SBATCH --time=24:00:00
#SBATCH --output=slurm-%x-%j.out

# Submit from this script's directory (paths below are relative to it):
#   cd evaluation/weather && sbatch run_question_answering.sh
# Run locally (e.g. Git Bash on Windows), with options from the environment
# (see evaluation/setup_env.sh); the optional argument limits the samples:
#   cd evaluation/weather && API_NAME=gpt-5.4-mini MODE=timeseries_only bash run_question_answering.sh 3
# MODE=timeseries_only leaves the weather event report out of the prompt.

cd "${SLURM_SUBMIT_DIR:-$(dirname "$0")}"
ALLOWED_MODES="timeseries_only combined"
. ../setup_env.sh

# Generate lists first with evaluation/run_make_parity_subsets.sh.
# Override SUBSETS_DIR to use a custom --output-dir (relative to this directory).
SUBSETS_DIR="${SUBSETS_DIR:-../../subsets}"

SETTING="${SETTING:-long}" # select from ["long", "short"]

# Combined runs keep their original folder; other modes get a subfolder.
MODE_DIR=""
if [ "$MODE" != "combined" ]; then
    MODE_DIR="/${MODE}"
fi

python mcqa.py \
    --subset_file="${SUBSETS_DIR}/weather_mcqa_${SETTING}.json" \
    --dataset_folder="../../data/processed/weather/QA${SETTING}" \
    --save_path="../../results/weather/question_answering_${SETTING}/${API_NAME}${MODE_DIR}${LIMIT_SUFFIX}" \
    --model=$API_NAME $BATCH_FLAGS $LIMIT_FLAGS \
    --mode=$MODE \
    --setting=$SETTING
