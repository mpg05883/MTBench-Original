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

module load miniconda
eval "$(conda shell.bash hook)"
conda activate MTBench

cd "${SLURM_SUBMIT_DIR:-$(dirname "$0")}"

# Generate lists first with evaluation/run_make_parity_subsets.sh.
# Override SUBSETS_DIR to use a custom --output-dir (relative to this directory).
SUBSETS_DIR="${SUBSETS_DIR:-../../subsets}"

API_NAME="gpt-5.1"
SETTING="${SETTING:-long}" # select from ["long", "short"]

python mcqa.py \
    --subset_file="${SUBSETS_DIR}/weather_mcqa_${SETTING}.json" \
    --dataset_folder="../../data/processed/weather/QA${SETTING}" \
    --save_path="../../results/weather/question_answering_${SETTING}/${API_NAME}" \
    --model=$API_NAME \
    --setting=$SETTING
