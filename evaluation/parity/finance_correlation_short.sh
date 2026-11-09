#!/bin/bash
# GPT-5.4-mini parity run of finance_correlation_short (finance correlation prediction, short horizon) with the
# original evaluator, one array task per input setting: 0 = TS-only,
# 1 = TS+text. The job body and flags are in cell_job.sh in this folder.
#
# From the repo root:
#   mkdir -p logs/parity
#   sbatch evaluation/parity/finance_correlation_short.sh
#   sbatch evaluation/parity/finance_correlation_short.sh --repeat

#SBATCH --job-name=parity-ref-mini-finance-correlation-short
#SBATCH --array=1
#SBATCH --partition=day
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=06:00:00
#SBATCH --output=./logs/parity/%x/%A/out/%a.out
#SBATCH --error=./logs/parity/%x/%A/err/%a.err
#SBATCH --mail-user=mike.gee@yale.edu
#SBATCH --mail-type=FAIL

cell="finance_correlation_short"
conditions=(combined)
source ./evaluation/parity/cell_job.sh "$@"
