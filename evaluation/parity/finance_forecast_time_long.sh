#!/bin/bash
# GPT-5.4-mini parity run of finance_forecast_time_long (finance forecasting, long horizon) with the
# original evaluator, one array task per input setting: 0 = TS-only,
# 1 = TS+text. The job body and flags are in cell_job.sh in this folder.
#
# From the repo root:
#   mkdir -p logs/parity
#   sbatch evaluation/parity/finance_forecast_time_long.sh
#   sbatch evaluation/parity/finance_forecast_time_long.sh --repeat

#SBATCH --job-name=parity-ref-mini-finance-forecast-time-long
#SBATCH --array=0-1
#SBATCH --partition=day
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=12:00:00
#SBATCH --output=./logs/parity/%x/%A/out/%a.out
#SBATCH --error=./logs/parity/%x/%A/err/%a.err
#SBATCH --mail-user=mike.gee@yale.edu
#SBATCH --mail-type=FAIL

cell="finance_forecast_time_long"
conditions=(timeseries_only combined)
source ./evaluation/parity/cell_job.sh "$@"
