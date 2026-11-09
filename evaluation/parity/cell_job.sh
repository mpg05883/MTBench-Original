#!/bin/bash
# Shared body of the GPT-5.4-mini parity scripts in this folder (one per
# horizon-domain-task tuple), mirroring the MTBench repo's
# cli/2026-11-02_refactor_evaluation_parity/mini/. Not submitted by itself:
# each <cell>.sh holds the #SBATCH header, sets `cell` and `conditions`, and
# sources this file.
#
# Each array task runs the cell's original evaluator for gpt-5.4-mini on one
# input setting, on the cell's 300-item list in subsets/<cell>.json, with
# AZURE_SEED=42 (the seed the MTBench code sends):
#   array index 0 -> timeseries_only (TS-only)
#   array index 1 -> combined        (TS+text)
# Correlation and MCQA cells run only `combined` (as in MTBench), so their
# scripts use --array=1.
#
# Results: results/parity/gpt-5.4-mini-seed42[-repeat]/<cell>/<condition>/,
# the same <cell>/<condition> layout as MTBench's results folder. A cell.done
# marker there makes a resubmit skip the finished cell.
#
# How to run (from the repo root):
#   mkdir -p logs/parity
#   sbatch evaluation/parity/<cell>.sh
#   sbatch evaluation/parity/<cell>.sh --repeat
#   bash evaluation/parity/<cell>.sh --limit 3
# Every run calls the model (Azure spend); use --limit for a cheap check.
# Without SLURM (bash), the cell's conditions run one after the other, with
# logs in logs/parity/<job-name>/local-<timestamp>/.
#
# Flags:
#   --repeat     - write to gpt-5.4-mini-seed42-repeat/ (the second run, for
#                  run-to-run disagreement)
#   --limit <n>  - evaluate only the first n items; the results name gets a
#                  "-dev" suffix so a check never marks the real cell as done
#
# Environment:
#   PYTHON_BIN   - a python with the MTBench env's packages, used instead of
#                  activating the conda env (e.g. locally on Windows:
#                  PYTHON_BIN=~/anaconda3/envs/MTBench/python.exe)
#   CONVERTED_DIR - finance converted folder with short/ and long/ (default:
#                  data/processed/finance_converted)

api_name="gpt-5.4-mini"
# Array index -> input setting.
all_conditions=(timeseries_only combined)
job_name="parity-ref-mini-${cell//_/-}"

if [[ -z "${cell:-}" || ${#conditions[@]} -eq 0 ]]; then
    echo "cell_job.sh: set cell and conditions before sourcing it" >&2
    exit 1
fi

repo_root="$(pwd)"
if [[ ! -d "${repo_root}/evaluation/parity" ]]; then
    echo "Run this from the MTBench-Original repo root" >&2
    exit 1
fi

repeat=false
limit=""
while [[ $# -gt 0 ]]; do
    case "$1" in
    --repeat)
        repeat=true
        shift
        ;;
    --limit)
        limit="$2"
        shift 2
        ;;
    *)
        echo "Unknown argument: $1 (expected --repeat or --limit)" >&2
        exit 1
        ;;
    esac
done
if [[ -n "$limit" && "$limit" == *[!0-9]* ]]; then
    echo "Invalid --limit: $limit (must be a positive integer)" >&2
    exit 1
fi

# Outside SLURM, tee the output into log files laid out like the SLURM ones.
if [[ -z "${SLURM_JOB_ID:-}" ]]; then
    local_log_dir="logs/parity/${job_name}/local-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$local_log_dir"
    exec > >(tee -a "${local_log_dir}/out.out") \
        2> >(tee -a "${local_log_dir}/err.err" >&2)
    echo "Mode: local (logs in ${local_log_dir})"
else
    echo "Mode: SLURM job ${SLURM_JOB_ID}, array task ${SLURM_ARRAY_TASK_ID:-none}"
fi

# The input settings this task runs: one per array task, or all of the cell's
# conditions without SLURM.
if [[ -n "${SLURM_ARRAY_TASK_ID:-}" ]]; then
    if [[ ! "$SLURM_ARRAY_TASK_ID" =~ ^[01]$ ]]; then
        echo "Array index ${SLURM_ARRAY_TASK_ID} is not 0 (timeseries_only) or 1 (combined)" >&2
        exit 1
    fi
    run_conditions=("${all_conditions[$SLURM_ARRAY_TASK_ID]}")
    if [[ " ${conditions[*]} " != *" ${run_conditions[0]} "* ]]; then
        echo "${cell} has no ${run_conditions[0]} condition (only: ${conditions[*]})" >&2
        exit 1
    fi
else
    run_conditions=("${conditions[@]}")
fi

# Python: PYTHON_BIN, or the MTBench conda env via setup_env.sh. setup_env.sh
# is sourced inside a function so it doesn't see this script's arguments.
activate_env() {
    # setup_env.sh reads MODE and LIMIT; give it valid values.
    MODE=combined LIMIT="" . "${repo_root}/evaluation/setup_env.sh"
}
if [[ -n "${PYTHON_BIN:-}" ]]; then
    python_bin="$PYTHON_BIN"
else
    activate_env
    python_bin="python"
fi

export AZURE_SEED=42
results_name="${api_name}-seed${AZURE_SEED}"
if [[ "$repeat" == "true" ]]; then
    results_name="${results_name}-repeat"
fi
limit_flags=()
if [[ -n "$limit" ]]; then
    results_name="${results_name}-dev"
    limit_flags=(--limit="$limit")
fi

converted_dir="${CONVERTED_DIR:-data/processed/finance_converted}"
converted_dir="$(cd "$converted_dir" 2>/dev/null && pwd || echo "${repo_root}/${converted_dir}")"
processed="${repo_root}/data/processed"
subsets="${repo_root}/subsets"

# Set domain, script and args for the cell (the same evaluator and flags as
# its evaluation/<domain>/run_*.sh).
case "$cell" in
finance_*_short | weather_*_short)
    setting=short
    ;;
*)
    setting=long
    ;;
esac
# Finance correlation and MCQA pick the long prompts only when
# --dataset_folder is exactly "../../data/processed/finance/QAlong"
# (correlation_prediction.py and mcqa.py, line 83); an absolute path gives
# the short prompts. So pass the path relative to evaluation/finance, where
# the evaluator runs, as evaluation/finance/run_question_answering.sh does.
finance_qa_folder="../../data/processed/finance/QA${setting}"
if [[ "$cell" == weather_* ]]; then
    if [[ "$setting" == short ]]; then in_days=7; out_days=1; else in_days=14; out_days=3; fi
    weather_pairs="${processed}/weather/aligned_in${in_days}days_out${out_days}days"
fi

case "$cell" in
finance_trend_*)
    domain=finance
    script=trend_classification.py
    args=(--dataset_folder="${converted_dir}/${setting}")
    ;;
finance_forecast_*)
    domain=finance
    script=value_prediction.py
    indicator="${cell#finance_forecast_}"
    indicator="${indicator%_"${setting}"}"
    args=(--dataset_folder="${converted_dir}/${setting}" --indicator="$indicator")
    ;;
finance_correlation_*)
    domain=finance
    script=correlation_prediction.py
    args=(--dataset_folder="$finance_qa_folder")
    ;;
finance_mcqa_*)
    domain=finance
    script=mcqa.py
    args=(--dataset_folder="$finance_qa_folder")
    ;;
weather_trend_*)
    domain=weather
    script=trend_classification.py
    past_future="${cell#weather_trend_}"
    past_future="${past_future%_"${setting}"}"
    args=(--dataset_folder="$weather_pairs" --in_days="$in_days"
        --out_days="$out_days" --past_future="$past_future")
    ;;
weather_forecast_*)
    domain=weather
    script=temperature_forecast.py
    args=(--dataset_folder="$weather_pairs" --in_days="$in_days" --out_days="$out_days")
    ;;
weather_indicator_*)
    domain=weather
    script=indicator_prediction.py
    args=(--dataset_folder="$weather_pairs" --in_days="$in_days" --out_days="$out_days")
    ;;
weather_mcqa_*)
    domain=weather
    script=mcqa.py
    args=(--dataset_folder="${processed}/weather/QA${setting}" --setting="$setting")
    ;;
*)
    echo "Unknown cell: ${cell}" >&2
    exit 1
    ;;
esac

echo "Cell: ${cell}; conditions: ${run_conditions[*]}; results: ${results_name}; python: ${python_bin}"

# The evaluators import their neighbours relative to their own folder.
cd "${repo_root}/evaluation/${domain}"
status=0
for condition in "${run_conditions[@]}"; do
    save_path="${repo_root}/results/parity/${results_name}/${cell}/${condition}"
    if [[ -f "${save_path}/cell.done" ]]; then
        echo "${cell}/${condition}: skipped (done)"
        continue
    fi
    mkdir -p "$save_path"
    echo "${cell}/${condition}: running ${script}"
    if "$python_bin" "$script" \
        --subset_file="${subsets}/${cell}.json" \
        --save_path="$save_path" \
        --model="$api_name" \
        --mode="$condition" \
        "${args[@]}" "${limit_flags[@]}"; then
        echo "done" >"${save_path}/cell.done"
        echo "${cell}/${condition}: done"
    else
        echo "${cell}/${condition}: failed" >&2
        status=1
    fi
done
exit "$status"
