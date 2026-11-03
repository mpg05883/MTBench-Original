#!/bin/bash
#SBATCH --job-name=fin_question_answering
#SBATCH --partition=day
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=4G
#SBATCH --time=24:00:00
#SBATCH --output=slurm-%x-%j.out

# Submit from this script's directory (paths below are relative to it):
#   cd evaluation/finance && sbatch run_question_answering.sh

module load miniconda
eval "$(conda shell.bash hook)"
conda activate MTBench

cd "${SLURM_SUBMIT_DIR:-$(dirname "$0")}"

# Generate lists first with evaluation/run_make_parity_subsets.sh.
# Override SUBSETS_DIR to use a custom --output-dir (relative to this directory).
SUBSETS_DIR="${SUBSETS_DIR:-../../subsets}"

API_NAME="gpt-5.1"
# Set BATCH_FLAGS="--batch --wait" to use the Batch API (see evaluation/batch.py).
BATCH_FLAGS="${BATCH_FLAGS:-}"
SETTING="${SETTING:-long}"

python correlation_prediction.py \
    --subset_file="${SUBSETS_DIR}/finance_correlation_${SETTING}.json" \
    --dataset_folder="../../data/processed/finance/QA${SETTING}" \
    --save_path="../../results/finance/correlation_${SETTING}/${API_NAME}" \
    --model=$API_NAME $BATCH_FLAGS
    

python mcqa.py \
    --subset_file="${SUBSETS_DIR}/finance_mcqa_${SETTING}.json" \
    --dataset_folder="../../data/processed/finance/QA${SETTING}" \
    --save_path="../../results/finance/mcqa_${SETTING}/${API_NAME}" \
    --model=$API_NAME $BATCH_FLAGS

