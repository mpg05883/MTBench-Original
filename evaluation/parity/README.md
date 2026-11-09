# GPT-5.4-mini parity runs

These SLURM array scripts run the original evaluators with GPT-5.4-mini on
the 300-item parity subsets (`subsets/<cell>.json`). Each
horizon-domain-task tuple has its own script. They mirror the MTBench repo's
`cli/2026-11-02_refactor_evaluation_parity/mini/`, and the two sets of
results are compared item by item in MTBench's
`experiments/2026-11-02_refactor_evaluation_parity/view_results.ipynb`.

- `<cell>.sh` (21 scripts) holds the `#SBATCH` header and the cell name.
  `cell_job.sh` is the shared body, which maps the cell to its evaluator and
  flags (the same as `evaluation/<domain>/run_*.sh`).
- Array index 0 runs `timeseries_only` and index 1 runs `combined`.
  Correlation and MCQA run only `combined` (`--array=1`), as in MTBench.
- `AZURE_SEED=42` is exported, so every request sends seed 42.
- Results go to `results/parity/gpt-5.4-mini-seed42/<cell>/<condition>/`.
  With `--repeat` they go to `...-seed42-repeat/`, and with `--limit N` the
  name gets a `-dev` suffix.
- A `cell.done` marker there makes a resubmit skip the cell.
- `finance_trend_short` has no script: it was already run.

## Before submitting on the cluster

- The `MTBench` conda env must exist (`evaluation/setup_env.sh` activates it
  through `module load miniconda`).
- `.env` must have `OPENAI_BASE_URL`, `AZURE_FOUNDRY_API_KEY` and
  `AZURE_DEPLOYMENT_GPT_5_4_MINI`.
- Three data inputs must be in place:
  - `subsets/` from `evaluation/run_make_parity_subsets.sh`;
  - `data/processed/finance_converted/{short,long}`;
  - `data/processed/{finance,weather}`.

## Run (from the repo root)

Every run calls Azure. Check one cell with `--limit 3` first.

```bash
mkdir -p logs/parity
sbatch evaluation/parity/weather_forecast_short.sh --limit 3   # check
for f in evaluation/parity/[fw]*.sh; do
  sbatch "$f"            # first run
  # sbatch "$f" --repeat # second run
done
```

Locally (no SLURM), `bash evaluation/parity/<cell>.sh` runs the conditions
one after the other. Set `PYTHON_BIN` to the env's python if conda can't be
activated in a non-interactive shell (e.g. Git Bash on Windows).

## Copy into MTBench

```bash
cp -r results/parity/gpt-5.4-mini-seed42/* \
  ../MTBench/experiments/2026-11-02_refactor_evaluation_parity/results/azure-gpt-5.4-mini-reference-seed42/
cp -r results/parity/gpt-5.4-mini-seed42-repeat/* \
  ../MTBench/experiments/2026-11-02_refactor_evaluation_parity/results/azure-gpt-5.4-mini-reference-seed42-repeat/
```
