# Provenance: inventory of the original MTBench code

This is a file-by-file inventory of the original MTBench repository, written so that later refactor steps can port from
it. Nothing here was copied into this repo; every file was read with `git show <hash>:<path>`.

+ Source: `upstream` = <https://github.com/Graph-and-Geometric-Learning/MTBench.git>
+ **Pinned commit: `394a9d274403e93a08b24c2a0b7af461615ce302`** (`upstream/mainline`, 2026-02-17, "update HF link")
+ Note: the task brief said `upstream/refactor`, but upstream has no such branch (`git ls-remote upstream` shows only
  `mainline`). `mainline` was pinned with the user's OK.
+ Files at the pinned commit: **40** (`git ls-tree -r --name-only <hash>`). Each is listed exactly once below.
+ Inventoried: 2026-11-01. Imports were extracted with `ast` (stdlib / third-party / intra-repo split), not taken from
  `requirement.txt`.
+ Python used by the originals: README says 3.10.14, but `evaluation/finance/value_prediction.py` needs 3.12+ (see its
  entry), so the code as pushed cannot have run on 3.10.

Kinds used: library logic, experiment entry point, CLI/shell wrapper, data download, data prep, config, dead/unused
(plus "docs/asset" for README and images).

## Reading guide: traits shared by all `evaluation/**` entry points ("E")

Every evaluation script (`evaluation/{finance,weather}/*.py` except `meta_prompt.py`) shares this skeleton, so the
per-file entries only mention differences.

+ Module-level script, no `main()`; `argparse` at import time.
+ `sys.path.append("../..")` plus `from evaluation.utils import ...` and `from meta_prompt import ...` only work when the
  working directory is the script's own folder (`cd evaluation/<domain>`, which the README instructs). `meta_prompt` is
  resolved from the script dir, which is the only reason the two `meta_prompt.py` files do not collide.
+ Reads every `*.json` in `--dataset_folder`, extracts a few fields, loops over samples calling one LLM, and writes
  `<save_path>/results.json` every 20 samples and at the end.
+ Model dispatch is an `if/elif` ladder on `--model` (`gpt-4o`, `sonnet`, `llama`, `gemini`, `deepseek`, `o1`, `r1`),
  copy-pasted in every script; each branch post-processes with `.strip().replace('"', '')`.
+ `llama` branch lazily imports `torch` and `transformers` and builds a `transformers.pipeline` for
  `meta-llama/Meta-Llama-3.1-8B-Instruct` (gated model; needs HF auth; needs `accelerate` for `device_map="auto"`).
+ API keys are module constants in `evaluation/api_call.py`, not env vars.
+ Errors inside the sample loop are caught with a bare `except Exception` and printed; failed samples are silently dropped
  from the results and the accuracy/metric denominators.
+ No seeds; sampling temperature for OpenAI defaults to 0.7 in `send_to_openai_chatgpt`.

## Per-file inventory

### Repo root

#### `.gitignore`
+ Purpose: standard Python gitignore plus `data/`, `logs/`, `wandb/`, `save/`, `tmpdata/`, `.unison*/`.
+ Kind: config.
+ Imports: none. I/O: none.
+ Hardcoded: none.
+ Destination: drop; the template has its own `.gitignore`. Note `save/` and `tmpdata/` hint at directories the original
  authors used locally.

#### `README.md`
+ Purpose: project description, folder structure, download/eval instructions, baseline result tables, citation.
+ Kind: docs/asset.
+ Imports: none.
+ Hardcoded: describes `requirements.txt` but the file is `requirement.txt`; says Python 3.10.14 / conda; says
  `cd evaluation/finance && bash run_trend_classification.sh`; its sample `save_path` (`${API_NAME}_${MODE}`) differs from
  the actual script (`${API_NAME}/${MODE}`).
+ Destination: drop as a file; mine it for `docs/datasets.md` (task definitions, dataset stats, baseline numbers to
  reproduce) in a later step.
+ Open: baseline numbers (GPT-4o, Gemini, Claude, DeepSeek) are the reproduction targets; confirm which prompts/modes
  produced them.

#### `download_processed_dataset.py`
+ **Replaced** by `scripts/download/processed_mtbench.py`, `scripts/download/raw_mtbench.py` and `cli/download/*.sh`. Same local folders under the repo's `data/`; no flags or dataset selection. The earlier `mtbench.data.download` registry (with `--dry-run`, `--domain`, `GGLabYale/` ids) was removed.
+ Purpose: downloads the 8 pre-processed HF datasets (finance + weather, short + long, aligned pairs and QA).
+ Kind: data download.
+ Third-party: `huggingface_hub`. Stdlib: none. Intra-repo: none.
+ Outputs (cwd-relative): `./data/processed/finance/{aligned_in7days_out1days, aligned_in30days_out7days, QAshort,
  QAlong}`, `./data/processed/weather/{aligned_in7days_out1days, aligned_in14days_out3days, QAshort, QAlong}`.
  HF repos: `afeng/MTBench_finance_aligned_pairs_{short,long}`, `afeng/MTBench_finance_QA_{short,long}`,
  `afeng/MTBench_weather_aligned_pairs_{short,long}`, `afeng/MTBench_weather_QA_{short,long}`.
+ Hardcoded: paths relative to cwd (must run from repo root); HF user `afeng`; runs on import (no `main`); no auth.
+ Destination: `scripts/download/processed_mtbench.py` (`resolve_data_dir()`), invoked by
  `cli/download/processed_mtbench.sh`. Writes into `data/processed/` (allowed), not `data/raw/`.
+ Open: the weather "QA" folders hold files with top-level `question`/`answer`, while finance QA holds nested `MCQA`.
  Confirm schemas after download. README links the collection under `GGLabYale`, code uses `afeng`; check both resolve.

#### `download_raw_dataset.py`
+ **Ported in step 6** together with `download_processed_dataset.py` (same files as above). Differences: raw datasets are only downloaded with `--raw`, never by default; `afeng/MTBench_weather_news` keeps its `afeng/` id because it has not moved.
+ Purpose: downloads the 4 raw HF datasets (finance news, finance stock series, weather text, weather series).
+ Kind: data download.
+ Third-party: `huggingface_hub`. Stdlib/intra-repo: none.
+ Outputs (cwd-relative): `./data/raw/finance/news_labeled_20000`, `./data/raw/finance/stock_ts`,
  `./data/raw/weather/text`, `./data/raw/weather/timeseries` (HF: `afeng/MTBench_finance_news`,
  `MTBench_finance_stock`, `MTBench_weather_news`, `MTBench_weather_temperature`).
+ Hardcoded: same as above. **Writes into repo-root `data/raw/`**, which AGENTS.md forbids unless the user explicitly asks.
+ Destination: `scripts/download_raw_dataset.py`; never run it without an explicit user request.
+ Open: the raw weather layout (`text/`, `timeseries/`) must be matched to what `data_preparation/weather/create_pairs.py`
  expects (see its entry); not verifiable without downloading.

#### `requirement.txt`
+ Purpose: pip requirements.
+ Kind: config.
+ Content: `pandas==1.5.3, gdown==5.2.0, huggingface-hub==0.29.0, anthropic==0.43.1, openai==1.59.7, google==3.0.0,
  google-auth==2.38.0, google-genai==1.2.0, numpy==1.24.4, matplotlib==3.9.0, scikit-learn==1.5.0`, unpinned
  `transformers`, `torch`, plus the stdlib names `pathlib, json, datetime, argparse, re`.
+ Problems: stdlib names are not valid requirements (and `pathlib` on PyPI is an obsolete backport that breaks Python 3);
  `google==3.0.0` is an unrelated search package; see "Dependency summary" for what is actually imported.
+ Destination: drop. Step 4 builds the uv environment from the import analysis instead.

### Assets (documentation images)

#### `assets/finance_duration.png`
+ Purpose: README figure, distribution of finance news impact duration. Kind: docs/asset (binary, 113 KB).
+ Destination: drop for now; reachable via the upstream link. Revisit if figures go into `docs/`.

#### `assets/finance_sentiment.png`
+ Purpose: finance sentiment distribution figure; **not referenced by the README**. Kind: docs/asset (83 KB).
+ Destination: drop.

#### `assets/finance_type.png`
+ Purpose: README figure, finance report type distribution. Kind: docs/asset (100 KB).
+ Destination: drop for now.

#### `assets/mtbench.png`
+ Purpose: README logo. Kind: docs/asset (540 KB).
+ Destination: drop.

#### `assets/weather_duration.png`
+ Purpose: README figure, severe weather duration distribution. Kind: docs/asset (46 KB).
+ Destination: drop for now.

#### `assets/weather_event.png`
+ Purpose: README figure, weather event type distribution. Kind: docs/asset (79 KB).
+ Destination: drop for now.

### `data_preparation/finance/`

#### `data_preparation/finance/utils.py`
+ **Ported in step 6** to `src/mtbench/data/finance/`: `indicators.py` (SMA, EMA, MACD, Bollinger, `calculate_technical_indicators`), `trend.py` (`calculate_stock_trend`, bins, sentiment mappings), `windows.py` (`to_timedelta`, the pair sampler), `io.py` (JSON and ISO 8601 helpers), `plot.py` (`plot_timeseries_with_reference`). Not ported: `calculate_moving_average` (unused). Behavior unchanged; quirks kept and marked `# NOTE:`. Parity fixtures: `tests/mtbench/data/finance/fixtures/{finance,windows}_parity.json`.
+ Purpose: grab-bag for finance prep: plotting, time-window sampling around an event, trend/bin labelling, technical
  indicators (SMA, EMA, MACD, Bollinger), JSON/ISO8601 helpers.
+ Kind: library logic.
+ Third-party: `numpy`, `pandas`, `matplotlib` (`pyplot`, `dates`). Stdlib: `datetime`, `json`, `os`, `random`.
  Intra-repo: none.
+ Functions: `plot_timeseries_with_reference`, `sample_a_stock_pair_flexible_units_given_event`, `calculate_stock_trend`,
  `save_dict_to_local_json`, `read_json_from_local`, `read_folder_of_json`, `convert_iso8601_to_datetime_and_timestamp`,
  `calculate_moving_average` (unused), `compute_sma`, `compute_ema`, `compute_macd`, `compute_bollinger_bands`.
+ I/O: reads/writes JSON and PNG at caller-supplied paths. No env vars.
+ Hardcoded/assumptions: raw series assumed to be 5-minute bars (`sample_every = seconds / (5*60)`); `to_timedelta`
  accepts `months`, but `timedelta(months=...)` raises `TypeError`; uses deprecated `datetime.utcfromtimestamp`.
+ Destination: split into `src/mtbench/data/finance/windows.py` (pair sampling), `.../indicators.py`,
  `.../trend.py`, `src/mtbench/utils/io.py` (JSON helpers), `src/mtbench/utils/plot.py` (the plot function).
+ Surprising: `sample_a_stock_pair...` returns `datetime.timestamp()` of *naive UTC* datetimes, which Python interprets as
  local time, so the stored `input_timestamps` shift with the machine's timezone; eval scripts then read them with
  `datetime.fromtimestamp` (local) so it round-trips only on the same timezone. The docstring of
  `convert_iso8601...` says nanoseconds but it returns milliseconds. Value lookup uses `ts in list` inside a
  comprehension (O(n^2)) and duplicates timestamps would duplicate values. `plot_...` colours are random and unseeded.

#### `data_preparation/finance/create_pairs.py`
+ **Ported in step 6** to `src/mtbench/data/finance/pairs.py` (`build_pairs`) and `scripts/data/prepare_finance_pairs.py`. The helpers `return_news_and_ts_sentiment` and `calculate_technical_indicators` moved to `trend.py` and `indicators.py`. Differences: paths and windows are arguments (no `/home/ubuntu` defaults), `logging` instead of `print`, new `--max-pairs` and `--no-plots` options (defaults keep the original behavior). **The zero-pairs bug is kept**: through the script, `read_folder_of_json` wraps articles, so every article is skipped. Parity fixture: `pairs_parity.json`, produced by running the original with the wrapper removed.
+ Purpose: for each labelled news article, sample an input/output price window around its publication time, compute
  trend bins, indicators and a news-vs-price sentiment "alignment" flag, and save JSON + PNG per pair.
+ Kind: data prep (module-level script).
+ Third-party: `numpy`. Stdlib: `argparse`, `datetime`, `os`, `pathlib`, `random`, `sys`. Intra-repo: `utils`
  (finance `utils.py`, via `sys.path.append("../..")` and cwd).
+ Inputs: `--text_folder` (labelled news JSON files), `--ts_folder` (one `<TICKER>.json` per ticker with
  `real_timestamp` (ms) and `open`). Outputs: `--save_folder/<idx>_<ticker>.json` and `visualization/<idx>_<ticker>.png`.
+ Hardcoded: default `--ts_folder` and `--save_folder` are `/home/ubuntu/time/...`; `event_position_ratio=0.9` (only used
  if the event timestamp is None, which never happens here); bins `[-4,-2,2,4]`%; seeds `random.seed(42)`,
  `np.random.seed(42)`; windows use the `open` column only; trend statistic is `mean`.
+ Destination: `scripts/data/prepare_finance_pairs.py` (thin argparse), logic into `src/mtbench/data/finance/pairs.py`.
+ **Likely bug:** `read_folder_of_json` returns `[{"file_name":..., "data":...}]`, but the loop tests
  `"content" not in news or "tickers" not in news` on the wrapper dict, so every article is skipped and no pairs are
  written. Either the published script differs from what produced the HF data, or there is a missing unwrap
  (`news = news["data"]`). Needs confirmation against the HF processed files.
+ Also: `all(ticker in all_ticker_set ...)` skips an article if any ticker lacks a series; `global_idx` counts failures
  so output indices have gaps; output folder naming in the wrapper (`pair_in_7days_5minutes_out_...`) differs from the
  HF names (`aligned_in7days_out1days`).

#### `data_preparation/finance/create_correlation.py`
+ **Not ported (empty upstream).** Nothing to port; the correlation labels exist only in the downloaded QA data.
+ Purpose: presumably generates the `news_price_correlation` labels for finance QA; **the file is empty (0 bytes).**
+ Kind: dead/unused.
+ Imports: none.
+ Destination: drop; cannot port. The correlation labels exist only in the downloaded `QA*` data.
+ Open: how `news_price_correlation` labels (five classes) were generated is unknown from this repo.

#### `data_preparation/finance/create_mcqa.py`
+ **Not ported (empty upstream).** Nothing to port; the MCQA questions exist only in the downloaded QA data.
+ Purpose: presumably generates finance MCQA (GPT-4o annotated) questions; **empty (0 bytes).**
+ Kind: dead/unused.
+ Destination: drop. Open: same as above for MCQA generation.

#### `data_preparation/finance/run_create_pairs.sh`
+ **Replaced in step 6** by `cli/data/finance_pairs.sh`: flags instead of edited variables, `--setting short|long` (the long values come from the README, not from the original repo), `--dev` (default) and `--real`.
+ Purpose: sets the 7 days / 5 minutes in, 1 day / 5 minutes out config and calls `create_pairs.py`.
+ Kind: CLI/shell wrapper.
+ Intra-repo: `create_pairs.py`. Inputs: `../../data/raw/finance/stock_ts`, `../../data/raw/finance/news_labeled_20000`.
  Output: `../../data/processed/finance/pair_in_7days_5minutes_out_1days_5minutes`.
+ Hardcoded: cwd-relative `../../` paths; only the short setting is present (no 30-day/hourly config for the long set).
+ Destination: `cli/<experiment>/prepare_finance_pairs.sh` sourcing `cli/utils/utils.sh`, parameterised by
  setting; output to `data/processed/` (not `data/raw/`).
+ Open: the long setting (30 d hourly in, 7 d hourly out) used for `aligned_in30days_out7days` is not in the repo.

#### `data_preparation/finance/run_create_correlation.sh`
+ **Not ported (calls an empty script).**
+ Purpose: one line, `python create_correlation.py`. Kind: dead/unused (calls an empty script).
+ Destination: drop.

#### `data_preparation/finance/run_create_mcqa.sh`
+ **Not ported (calls an empty script).**
+ Purpose: one line, `python create_mcqa.py`. Kind: dead/unused (calls an empty script).
+ Destination: drop.

### `data_preparation/weather/`

#### `data_preparation/weather/create_pairs.py`
+ **Ported in step 6** to `src/mtbench/data/weather/pairs.py` (`remove_duplicate_sentences`, `extract_temperature_data`, `interpolate_temperature_data`, `generate_pairs` = `generate_QA_data`), `scripts/data/prepare_weather_pairs.py` and `cli/data/weather_pairs.sh`. Only code change: `set_index(..., inplace=True)` became an assignment (pandas 3.1 deprecates `inplace`); the unused `sklearn` import is dropped. The `.loc[:, col] =` on the `head()` slice works under pandas 3.1 (checked). Parity fixture: `tests/mtbench/data/weather/fixtures/weather_pairs_parity.json` (original run on the same pandas, not on pandas 1.5).
+ Purpose: for each station, takes the N longest news reports, extracts the temperature windows around the report end
  date, resamples/interpolates to exact hourly length, and writes one JSON per (setting, top_n, station, index).
  Despite the name and the function `generate_QA_data`, it produces aligned pairs (no question/answer fields).
+ Kind: data prep.
+ Third-party: `numpy`, `pandas`, `tqdm`, `sklearn.metrics` (imported, never used). Stdlib: `argparse`, `json`, `os`,
  `re`. Intra-repo: none.
+ Inputs: `--station_file` (CSV with an `id` column), `--news_path/news_<id>.json` (`BEGIN_TIMESTAMP`, `END_TIMESTAMP`,
  `NEWS`), `--time_series_path/<id>_processed.json` (`DATE`, `temperature`). Output:
  `<QA_path>/<before>_<after>/<top_n>/<station>/<i>.json` with `text`, `input_timestamps`, `input_window`,
  `output_timestamps`, `output_window`.
+ Hardcoded: defaults `QA`, `news_data`, `time_series_data`, `stations.csv`, `--terms 14_3`, `--top_numbers 40`;
  "longest news" selection rule; window anchored on the *date* of `END_TIMESTAMP`, not its time.
+ Destination: `scripts/data/prepare_weather_pairs.py` + `src/mtbench/data/weather/pairs.py`
  (`remove_duplicate_sentences`, `extract_temperature_data`, `interpolate_temperature_data`).
+ Open: file names (`news_<id>.json`, `<id>_processed.json`, `stations.csv`) do not obviously match the raw HF layout
  `weather/text` and `weather/timeseries`; the raw-to-processed step that creates `_processed.json` is not in this
  repo. Synthetic reports for stations with no narrative (described in docs) are not generated here. Under pandas 3,
  `.loc[:, col] = ...` on the `head()` slice and `freq='h'` should be re-tested.

### `evaluation/` (shared)

#### `evaluation/api_call.py`
+ **Ported in step 8** to `src/mtbench/models/api.py` (needs the `model` extra). The `send_to_*` functions keep their models, parameters and return values (message objects for OpenAI chat and `o1`, strings for the others). Intentional differences: API keys come from the environment or `.env` (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `DEEPSEEK_API_KEY`) and a missing key raises `MissingAPIKeyError`; the SDKs are imported when a client is created; Gemini uses `from google import genai` (the original imported `google.generativeai` but called the `google-genai` client API); new `get_answer(model, prompt)` and `MODELS` replace the `if/elif` ladder copied into every evaluation script and always return a string, which also makes the `r1` model work (the scripts read `.content` on a string, so every `r1` sample failed); new `load_llama_pipeline()` replaces the pipeline built in seven scripts. Model ids and the SiliconFlow DeepSeek endpoint are kept as defaults (some ids are retired). Parity: the original functions were run in a scratchpad copy with fake SDKs, and the recorded requests and return values are in `tests/mtbench/models/fixtures/api_parity.json`; no real API was called.
+ Purpose: one function per LLM provider returning the reply text (or message object).
+ Kind: library logic.
+ Third-party: `openai`, `anthropic`, `google.generativeai` (imported as `genai`, but used as `genai.Client(...)`, which is
  the `google-genai` API; `from google import genai` would be correct). Stdlib/intra-repo: none.
+ Functions: `send_to_openai_chatgpt` (default `gpt-4`, `temperature=0.7`, `timeout=30`; returns the message object),
  `send_to_anthropic_claude` (`claude-3-5-sonnet-20241022`, `max_tokens=4096`; returns str), `send_to_google_gemini`
  (`gemini-2.0-flash`; str), `send_to_deepseek` / `send_to_deepseek_r1` (OpenAI client at
  `https://api.siliconflow.cn/v1/`, models `deepseek-ai/DeepSeek-V3` / `DeepSeek-R1`; both return **str**),
  `send_to_openai_o1` (`o1`, `timeout=30`; message object), `send_to_llama(content, pipeline)`.
+ Credentials: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_GEMINI_API`, `DEEPSEEK_API` are empty-string constants edited
  in place (risk of committing keys; the Anthropic comment mentions the env var but the code overrides it with `""`).
+ Destination: `src/mtbench/models/api.py` with keys from `.env` (`load_dotenv`), a registry dict of model name to
  callable (replaces every if/elif ladder), and a uniform return type (always `str`). Unit-test with mocked clients.
+ Surprising: the scripts call `response.content.strip()` for `r1`, but `send_to_deepseek_r1` already returns a str, so
  every `r1` sample raises `AttributeError` and is silently dropped. Retired/changed model ids
  (`claude-3-5-sonnet-20241022`, `gpt-4`) need updating. `max_tokens=None` plus `timeout=30` is too short for `o1`.

#### `evaluation/utils.py`
+ **Fully ported by step 15:** `save_to_json` in step 9 (`src/mtbench/utils/io.py`), `plot_series` and `format_time_difference` in step 15 (`src/mtbench/utils/plot.py`, `src/mtbench/utils/duration.py`, unchanged behavior; the plot test is a smoke test). The metric functions were ported in step 5 as follows.
+ **Partially ported in step 5** to `src/mtbench/eval/metrics.py` (tests: `tests/mtbench/eval/test_metrics.py`, parity
  fixture `tests/mtbench/eval/fixtures/metrics_parity.json` produced by the original at the pinned hash). Ported:
  `calculate_mape`, `calculate_acc`, `calculate_correlation_acc`, `calculate_mcqa_acc`, `compute_temperature_trend`,
  `get_temperature_diff_max_min`. `save_to_json` was ported in step 9 to `src/mtbench/utils/io.py`. Not yet ported: `format_time_difference`, `plot_series`. Behavior is
  unchanged; the quirks listed under "Surprising" are kept and marked `# NOTE:` in the code. Only differences: the
  positive/negative correlation label lists became module constants, and `.keys()` was dropped in a loop.
+ Purpose: metrics and small helpers shared by all tasks.
+ Kind: library logic.
+ Third-party: `numpy`, `matplotlib.pyplot`, `sklearn.linear_model`. Stdlib: `collections` (unused `defaultdict`),
  `json`, `os`. Intra-repo: none.
+ Functions: `format_time_difference`, `save_to_json`, `plot_series`, `calculate_mape` (skips zero ground truth),
  `calculate_acc` (substring match; optional label regrouping), `calculate_correlation_acc` (exact and "brief"
  positive/negative accuracy), `calculate_mcqa_acc`, `compute_temperature_trend` (slope >= 0.25 or diff >= 0.5 rules),
  `get_temperature_diff_max_min`.
+ I/O: writes JSON and PNG to caller paths.
+ Destination: `src/mtbench/eval/metrics.py` (+ `tests/mtbench/eval/test_metrics.py`); plotting separately.
+ Surprising: `calculate_mcqa_acc` does `predition[0].upper()` (IndexError on an empty reply, crashing the script after
  the loop); `calculate_acc` uses `ground_truth in predict` (substring), which can over-credit; the weather
  max/min ground truth takes only the *first* day's max/min even when `out_days` is 3; `reshape(len//24, 24)` assumes
  full days; no `matplotlib.use("Agg")` for headless cluster runs.

### `evaluation/finance/`

#### `evaluation/finance/meta_prompt.py`
+ **Ported in step 7** to `src/mtbench/eval/prompts/finance.py` (the six prompt builders) and `src/mtbench/eval/parsing.py` (`parse_val_prediction_response`, `parse_cls_response`). Prompts and parser behavior are unchanged; tests compare full prompts and parser results (including exceptions) with the original (`tests/mtbench/eval/fixtures/prompts_parity.json`). The three forecast builders were not merged, because their wording differs. The classification prompt contains a trailing space and whitespace-only lines that are part of the prompt (the parity test catches editors stripping them). Quirks are kept and marked `# NOTE:`.
+ Purpose: prompt builders and response parsers for finance tasks.
+ Kind: library logic.
+ Third-party: none. Stdlib: `re`, `typing`. Intra-repo: none.
+ Functions: `finance_mse_metaprompt_generation`, `finance_macd_metaprompt_generation`,
  `finance_bb_metaprompt_generation` (near-identical, three `mode`s each), `parse_val_prediction_response`,
  `finance_classification_metaprompt_generation`, `parse_cls_response` (`^^^label^^^` with a bare-`except` fallback),
  `finance_correlation_metaprompt_generation`, `finance_mcqa_metaprompt_generation` (both switch on `setting`).
+ Destination: `src/mtbench/eval/prompts/finance.py` + `src/mtbench/eval/parsing.py`; golden-string tests.
+ Surprising: the classification prompt hardcodes "1-hour intervals over the last month" even for the 7-day/5-minute short
  setting; `parse_cls_response` raises `IndexError` if no label is found (caught upstream, sample dropped);
  `text_only` mode exists in prompts but the wrappers only advertise `timeseries_only` and `combined`; the MSE prompt
  asks for "Predicted Prices" even when predicting MACD/BB.

#### `evaluation/finance/trend_classification.py`
+ **Ported in step 12** to `src/mtbench/eval/finance_trend.py` and `scripts/eval/finance_trend.py`, on the shared runner (using the `on_result` hook added in step 11 for the running five-way and three-way accuracy). `load_json_samples` now lets `extract_sample` return None to skip a file, which the original did for samples whose correct label is not a string (NaN). Same prompts, labels, parsing, `results.json` format (including `accumulated_acc_5way` and `accumulated_acc_3way`) and final accuracies as the original, checked by running the original script on six fixture samples with a fake model (one skipped for a NaN label, one model error, one answer without markers), in the `combined` and `text_only` modes, including the first prompt it sent and its console lines (`tests/mtbench/eval/fixtures/finance_trend_parity.json`). Differences: failed samples are also written to `failures.json` (still left out of the results and accuracies); sample files are read in name order; `--dry-run`, `--max-samples` and a required `--save-path` are new; `--setting long|short` only picks the default dataset folder (the original took the folder from its wrapper); when every sample fails the files are written first and the same `IndexError` follows. Kept: the times in the prompt are formatted in the machine's time zone and the prompt always says "1-hour intervals over the last month"; `timestamp_ms` is always None; a sample whose correct label is not one of the five labels is appended without accumulated fields before the three-way grouping raises `KeyError`.
+ Purpose: 5-class trend classification (bins of output percentage change) with optional news text; reports 5-way and 3-way
  accuracy.
+ Kind: experiment entry point (E).
+ Third-party: `torch`, `transformers` (lazy, llama only). Stdlib: `argparse`, `datetime`, `json`, `os`, `pathlib`,
  `sys`. Intra-repo: `meta_prompt` (finance), `evaluation.utils`, `evaluation.api_call`.
+ Inputs: aligned-pair JSON (`trend.output_bin_label`, `text.content`, `input_window`, `input_timestamps`). Outputs:
  `<save_path>/results.json`. Args: `--mode {timeseries_only,text_only,combined}`, `--model` (also `gpt-4o-mini`).
+ Hardcoded: label list in the prompt; 3-way regrouping dict (key typo `'negtive'` is harmless).
+ Destination: shared runner in `src/mtbench/eval/runner.py`; task config in `scripts/evaluate.py` (or an experiment).
+ Surprising: `"timestamp_ms" in data` checks the top level, so it is always `None` (unused anyway); `result_list[-1]`
  raises `IndexError` at the end if every sample failed; samples with non-string bin labels are skipped.

#### `evaluation/finance/value_prediction.py`
+ **Ported in step 16** to `src/mtbench/eval/finance_forecast.py` and `scripts/eval/finance_forecast.py`, on the shared forecast loop `src/mtbench/eval/forecast.py` introduced in step 15 (mean absolute percentage error enabled, and the `failed mse` console line kept). Same prompts, parsing, interpolation, error formulas, thresholds (mean squared error above 10 for `macd`, 100 for `time` and `bb`) and saved files as the original, checked by running the original script on six fixture samples with a fake model for each of the three series, including the first prompt (with its two times replaced by placeholders because the original formats them in the machine's time zone), its console lines and the files it wrote (`tests/mtbench/eval/fixtures/finance_forecast_parity.json`). Differences: samples that fail, and forecasts above the threshold, are listed in the new `failures.json`; `--indicator` must be one of `time`, `macd`, `bb` and is checked before any work (the original raised an error for every sample inside its error handler and finished without a result); `--dry-run`, `--max-samples` and a required `--save-path` are new; `--setting long|short` only picks the default dataset folder; sample files are read in name order; `llama` is not offered. Kept: the prompt's `pred_end_datetime` is the last value of the target series, not a date; the granularity text comes from float timestamps ("5.0 minutes"); a file without `text` or `technical` stops the run while loading.
+ Purpose: forecast the price series (`--indicator time`), MACD (`macd`) or upper Bollinger band (`bb`); reports
  MSE/MAE/RMSE/MAPE.
+ Kind: experiment entry point (E, without `llama`).
+ Third-party: `numpy` (+ `matplotlib` through `evaluation.utils`). Stdlib: `argparse`, `datetime`, `json`, `pathlib`,
  `sys`. Intra-repo: `meta_prompt` (finance), `evaluation.api_call`, `evaluation.utils`.
+ Inputs: aligned-pair JSON incl. `technical.{in,out}_{macd,upper_bb}`. Outputs: `<save>/output_details/<file>.json`,
  `<save>/visualizations/*.png`, `epoch_results.json`, `final_results.json`.
+ Hardcoded: **failure thresholds** (MSE > 10 for MACD, > 100 for time and BB) drop a sample from the means;
  the model reply is linearly interpolated to the ground-truth length before scoring.
+ Destination: shared runner + `src/mtbench/eval/forecast.py`.
+ Surprising: **syntax requires Python >= 3.12** (`f"{sample["filename"]}"` reuses the outer quote); template pins
  `>=3.11`. `--indicator` is both `required=True` and has a default. Outlier filtering changes reported metrics, so any
  reproduction must keep or document it. `final_results.json` averages only non-failed samples; `total_samples` counts all.

#### `evaluation/finance/correlation_prediction.py`
+ **Ported in step 13** to `src/mtbench/eval/finance_correlation.py` and `scripts/eval/finance_correlation.py`, on the shared runner. The sample reading that it had in common with `mcqa.py` (ticker and index from the file name, the price window, the news text, and the two times shown in the prompt) is now one shared module, `src/mtbench/eval/finance_samples.py`, which `finance_mcqa.py` uses as well (its public functions are unchanged). Same prompts, results format, `final_results.json` (exact and brief accuracy, `total_samples`, `model`) as the original, checked by running the original script on six fixture samples with a fake model for both settings, including the first prompt it sent and the files it wrote (`tests/mtbench/eval/fixtures/finance_correlation_parity.json`). Differences: failed samples are also written to `failures.json` (still left out of the results and the accuracies); the setting is the `--setting` argument instead of an exact string match on the dataset folder; sample files are read in name order; `--dry-run`, `--max-samples` and a required `--save-path` are new. Kept: the prompt times are formatted in the machine's time zone, a malformed file name stops the run while loading, and when no sample is scored `results.json` is written and `ZeroDivisionError` follows without a `final_results.json`.
+ Purpose: predict one of five news-price correlation classes; reports exact and "brief" accuracy.
+ Kind: experiment entry point (E).
+ Third-party: `torch`, `transformers` (lazy). Stdlib: `argparse`, `datetime`, `json`, `os`, `pathlib`, `sys`.
  Intra-repo: `meta_prompt` (finance), `evaluation.utils`, `evaluation.api_call`.
+ Inputs: QA JSON (`news_price_correlation`, `text`, `published_utc`, windows); ticker parsed from the file name
  (`<idx>_<TICKER>.json`). Outputs: `results.json`, `final_results.json`.
+ Hardcoded: `setting = "long"` only if `--dataset_folder == "../../data/processed/finance/QAlong"` (exact string),
  otherwise "short" (any absolute path or trailing slash silently selects the wrong prompt).
+ Destination: shared runner; derive `setting` from an explicit `--setting` arg.
+ Surprising: variable named `sticker` (sic) throughout.

#### `evaluation/finance/mcqa.py`
+ **Ported in step 10** to `src/mtbench/eval/finance_mcqa.py` and `scripts/eval/finance_mcqa.py`, on the shared runner. The flow it has in common with the weather task (result entries, model call, accuracy) now lives in `src/mtbench/eval/mcqa.py`, and `eval/weather_mcqa.py` calls it too (its public `evaluate` is unchanged). Same sample fields (`MCQA.question` / `MCQA.answer`, ticker and index from the file name), prompts, results format and accuracy as the original, checked by running the original script on five fixture samples with a fake model, for both settings, including the first prompt it sent (`tests/mtbench/eval/fixtures/finance_mcqa_parity.json`). Differences: failed samples are also written to `failures.json` (they are still left out of the results and the accuracy); the setting is the `--setting` argument instead of an exact string match on the dataset folder (`../../data/processed/finance/QAlong`, anything else silently gave the short prompts); sample files are read in name order; `--dry-run`, `--max-samples` and a required `--save-path` are new. Kept: the prompt times are formatted in the machine's time zone, and a sample file without `MCQA` or with a malformed name stops the run while loading.
+ Purpose: 4-way multiple-choice QA over (price series, news, question).
+ Kind: experiment entry point (E).
+ Third-party: `torch`, `transformers` (lazy). Stdlib: `argparse`, `datetime`, `json`, `os`, `pathlib`, `sys`.
  Intra-repo: `meta_prompt` (finance), `evaluation.utils`, `evaluation.api_call`.
+ Inputs: QA JSON with nested `MCQA.question` / `MCQA.answer`. Outputs: `results.json`; accuracy only printed.
+ Hardcoded: same exact-string `setting` check as above.
+ Destination: shared runner; **near-copy of `correlation_prediction.py`** (see duplication).
+ Surprising: accuracy is not saved to a file, only printed.

#### `evaluation/finance/run_trend_classification.sh`
+ **Replaced in step 12** by `cli/eval/finance_trend.sh`: a dry run is the default (no model call), `--real` calls the model and needs `--save-path`; `--setting`, `--mode` and `--model` are flags.
+ Purpose: runs `trend_classification.py` for GPT-4o, 30-day in / 7-day out, `combined`. Kind: CLI/shell wrapper.
+ Intra-repo: `trend_classification.py`. Reads `../../data/processed/finance/aligned_in30days_out7days`; writes
  `../../results/finance/trend_classification_in30_out7/<model>/<mode>`.
+ Hardcoded: model/mode/days at the top; cwd-relative paths; results at repo-root `results/`; no shebang or `set -e`.
+ Destination: `cli/baseline_repro/finance_trend_classification.sh` (sbatch, sources `cli/utils/utils.sh`), results to
  `experiments/<exp>/results/`.

#### `evaluation/finance/run_ts_forecast.sh`
+ **Replaced in step 16** by `cli/eval/finance_forecast.sh --indicator time`.
+ Purpose: runs `value_prediction.py --indicator time`. Kind: CLI/shell wrapper.
+ Intra-repo: `value_prediction.py`. Same data in; out to `../../results/finance/pred_time_in30_out7/<model>/<mode>`.
+ Hardcoded and destination: as above (`cli/baseline_repro/finance_ts_forecast.sh`).

#### `evaluation/finance/run_indicator_prediction.sh`
+ **Replaced in step 16** by `cli/eval/finance_forecast.sh --indicator macd` (or `bb`). The wrapper has a dry run by default and `--real` calls the model.
+ Purpose: runs `value_prediction.py --indicator macd`. Kind: CLI/shell wrapper.
+ Intra-repo: `value_prediction.py`. Output: `../../results/finance/pred_macd_in30_out7/...`. The comment lists
  `bb` as another option, which requires editing the file.
+ Destination: `cli/baseline_repro/finance_indicator_prediction.sh`, parameterised over `macd`/`bb`.

#### `evaluation/finance/run_question_answering.sh`
+ **Replaced in steps 10 and 13:** the multiple-choice call is `cli/eval/finance_mcqa.sh` and the correlation call is `cli/eval/finance_correlation.sh` (dry run by default, `--real` calls the model).
+ Purpose: runs `correlation_prediction.py` then `mcqa.py` for `SETTING=long`. Kind: CLI/shell wrapper.
+ Intra-repo: `correlation_prediction.py`, `mcqa.py`. Data: `../../data/processed/finance/QA${SETTING}`; out:
  `../../results/finance/{correlation,mcqa}_${SETTING}/<model>`.
+ Hardcoded: the folder path must equal exactly `../../data/processed/finance/QAlong` for the "long" prompt.
+ Destination: `cli/baseline_repro/finance_question_answering.sh`.

### `evaluation/weather/`

#### `evaluation/weather/__init__.py`
+ Purpose: empty package marker (0 bytes); `evaluation/` and `evaluation/finance/` have none.
+ Kind: dead/unused. Destination: drop (the `src/mtbench` package replaces it).

#### `evaluation/weather/meta_prompt.py`
+ **Ported in step 7** to `src/mtbench/eval/prompts/weather.py` (the four prompt builders) and `src/mtbench/eval/parsing.py` (the three `decode_*` functions). Prompts and parser behavior are unchanged. Intentional difference: the mode block that was copied into the trend, forecast and indicator builders is now one private helper, `_weather_mode_section`; the output is identical (parity-tested). Found while chaining the pieces: the ground-truth difference from `get_temperature_diff_max_min` is rounded to 1 decimal, but `decode_temperature_indicator` checks the answer's difference to 2 decimals (original behavior, kept).
+ Purpose: prompt builders and decoders for weather tasks.
+ Kind: library logic.
+ Third-party: none. Stdlib: `re`, `typing`. Intra-repo: none.
+ Functions: `temperature_trend_metaprompt_generation` (past/future), `temperature_forecast_metaprompt_generation`,
  `temperature_indicator_metaprompt_generation`, `weather_mcqa_metaprompt_generation`, `decode_temperature_indicator`
  (strict full-match regex, checks `max - min == diff`), `decode_temperature_trend_prediction` (exactly one of
  increasing/decreasing/stable), `decode_temperature_forecast`.
+ Destination: `src/mtbench/eval/prompts/weather.py` and `parsing.py`.
+ Surprising: the three prompt builders repeat the same three-mode block; MCQA prompt has "between{start}" with no space and
  always says the interval is 1 hour; the "past" trend task is computable from the input series alone, so text cannot
  help (a built-in unimodal shortcut worth noting for the validation-framework goal).

#### `evaluation/weather/trend_classification.py`
+ **Ported in step 11** to `src/mtbench/eval/weather_trend.py` and `scripts/eval/weather_trend.py`, on the shared runner. The runner gained an optional `on_result` hook (called after each new result, inside the error handling) so that the running `accumulated_acc` and the per-sample log line, which the original computed in the same `try` block, can be added without changing the other tasks. Same prompts, labels (`compute_temperature_trend`), parsing, `results.json` format (including `accumulated_acc`) and final accuracy as the original, checked by running the original script on five fixture samples with a fake model, for `past` and `future`, including the first prompt it sent and its console lines (`tests/mtbench/eval/fixtures/weather_trend_parity.json`). Differences: failed samples (model errors, unparsable answers, windows that are not whole days) are also written to `failures.json`, still left out of the results and accuracy; sample files are read in name order; `--dry-run`, `--max-samples` and a required `--save-path` are new; when every sample fails the files are written first and the same `IndexError` follows (the original raised before writing the final file). Kept: `--in-days` and `--out-days` only change the prompt text, and a `past_future` other than "past" gives the "past" wording with the "future" label.
+ Purpose: increasing/decreasing/stable classification; `--past_future past` labels the *input* window's slope,
  `future` compares the next day's mean with the last input day.
+ Kind: experiment entry point (E).
+ Third-party: `torch`, `transformers` (lazy). Stdlib: `argparse`, `datetime`, `json`, `os`, `pathlib`, `sys`.
  Intra-repo: `meta_prompt` (weather), `evaluation.utils`, `evaluation.api_call`.
+ Inputs: aligned-pair JSON (`input_window`, `output_window`, `text`, `input_timestamps`). Outputs: `results.json` with
  `accumulated_acc`.
+ Surprising: `result_list[-1]` crashes if all samples fail; labels are computed at eval time, not stored in the data.
+ Destination: shared runner.

#### `evaluation/weather/temperature_forecast.py`
+ **Ported in step 15** to `src/mtbench/eval/weather_forecast.py` and `scripts/eval/weather_forecast.py`, on a new shared forecast loop, `src/mtbench/eval/forecast.py`, that `evaluation/finance/value_prediction.py` will use as well (the provenance duplication table listed these two as near-copies). Same prompts, decoding, interpolation of the answer to the ground-truth length, error formulas and saved files as the original (`output_details/<sample>.json`, `visualizations/<sample>.png`, `epoch_results.json`, `final_results.json`), checked by running the original script on six fixture samples with a fake model (an exact forecast, a short one that needs interpolation, one above the error threshold, one model error, one unparsable answer, one close forecast), in the `combined` and `text_only` modes, including the first prompt, its console lines and the files it wrote (`tests/mtbench/eval/fixtures/weather_forecast_parity.json`). The mean squared and absolute errors are computed with numpy instead of scikit-learn (identical numbers in the parity test). Differences: samples that fail, and forecasts above the mean-squared-error threshold of 100 (which the original already left out of the averages), are listed in the new `failures.json` with `kind` "error" or "excluded"; `--dry-run`, `--max-samples` and a required `--save-path` are new; sample files are read in name order; `llama` is not offered (the original did not support it here); `--in-days` and `--out-days` only name the default dataset folder. Kept: everything for a sample, including building its prompt, is inside one error handler; `epoch_results.json` is only written after a sample that is kept in the averages; `total_samples` counts the excluded forecasts too.
+ Purpose: hourly temperature forecast; MSE/MAE/RMSE.
+ Kind: experiment entry point (E, without `llama`).
+ Third-party: `numpy`, `sklearn.metrics`. Stdlib: `argparse`, `datetime`, `json`, `pathlib`, `sys`. Intra-repo:
  `meta_prompt` (weather), `evaluation.api_call`, `evaluation.utils`.
+ Outputs: `output_details/`, `visualizations/`, `epoch_results.json`, `final_results.json`.
+ Hardcoded: samples with MSE > 100 are excluded from means; `--out_days` is parsed but unused.
+ Destination: shared forecast runner (twin of `finance/value_prediction.py`).

#### `evaluation/weather/indicator_prediction.py`
+ **Ported in step 14** to `src/mtbench/eval/weather_indicator.py` and `scripts/eval/weather_indicator.py`, on the shared runner (using the `on_result` hook for the per-sample errors). The sample reading that it had in common with the weather trend script is now `src/mtbench/eval/weather_samples.py`, which `weather_trend.py` uses as well. Same prompts, correct values (`get_temperature_diff_max_min`), answer decoding, `results.json` and `summary.json` (mean squared and absolute error of `diff`, `max` and `min`, computed with scikit-learn as before) as the original, checked by running the original script on five fixture samples with a fake model (one inconsistent answer, one model error), in the `combined` and `text_only` modes, including the first prompt it sent, its console lines and the files it wrote (`tests/mtbench/eval/fixtures/weather_indicator_parity.json`). Differences: failed samples are also written to `failures.json` (still left out of the results and the errors); sample files are read in name order; `--dry-run`, `--max-samples` and a required `--save-path` are new; `--out-days` only names the default dataset folder (the original accepted it and ignored it). Kept: the prompt always asks about the next 1 day, the correct values use only the first day of the next window, and with no scored sample the summary holds NaN and no error is raised.
+ Purpose: predict next-day max, min and max-min difference; MSE/MAE per quantity.
+ Kind: experiment entry point (E).
+ Third-party: `numpy`, `sklearn.metrics`, `torch`, `transformers` (lazy). Stdlib: `argparse`, `datetime`, `json`, `os`,
  `pathlib`, `sys`. Intra-repo: `meta_prompt` (weather), `evaluation.utils`, `evaluation.api_call`.
+ Outputs: `results.json`, `summary.json`.
+ Surprising: scores one-element lists with sklearn per sample (heavy for what it does); the ground truth uses day 1 only;
  `np.mean` of an empty list gives NaN if nothing parsed.
+ Destination: shared runner.

#### `evaluation/weather/mcqa.py`
+ **Ported in step 9** to `src/mtbench/eval/weather_mcqa.py` and `scripts/eval/weather_mcqa.py`, on top of the shared runner `src/mtbench/eval/runner.py` (loader, model call, result building, saving every 20 samples) that the other evaluation scripts will reuse. Same prompts, results format (`results.json` with `cnt`, `filename`, `question`, `ground_truth`, `predict`) and accuracy as the original, checked by running the original script on five fixture samples with a fake model (`tests/mtbench/eval/fixtures/weather_mcqa_parity.json`). Differences: (1) samples that fail are still left out of `results.json` and of the accuracy, as in the original, but are now also written to `failures.json` (`scored`, `failed`, and each failure's index, file, error type and message) and logged as "N scored, M failed"; (2) sample files are read in name order (the original used file-system order); (3) `--dry-run` prints the first prompt without calling a model, `--max-samples` limits the run, `--save-path` is required for a real run; (4) models come from `mtbench.models.api.get_answer`.
+ Purpose: weather MCQA (14-day or 7-day window by `--setting`).
+ Kind: experiment entry point (E).
+ Third-party: `torch`, `transformers` (lazy). Stdlib: `argparse`, `datetime`, `json`, `os`, `pathlib`, `sys`.
  Intra-repo: `meta_prompt` (weather), `evaluation.utils`, `evaluation.api_call`.
+ Inputs: QA JSON with top-level `question` and `answer` (differs from finance). Outputs: `results.json`.
+ Destination: shared runner.

#### `evaluation/weather/run_trend_classification.sh`
+ **Replaced in step 11** by `cli/eval/weather_trend.sh`: a dry run is the default (no model call), `--real` calls the model and needs `--save-path`; `--mode`, `--in-days`, `--out-days` and `--past-future` are flags.
+ Purpose: runs weather `trend_classification.py` (7 d in, 1 d out, `past`). Kind: CLI/shell wrapper.
+ Data: `../../data/processed/weather/aligned_in7days_out1days`; out: `../../results/weather/trend_classification_in7_out1/...`.
+ Destination: `cli/baseline_repro/weather_trend_classification.sh`.

#### `evaluation/weather/run_temperature_forecast.sh`
+ **Replaced in step 15** by `cli/eval/weather_forecast.sh`: a dry run is the default (no model call), `--real` calls the model and needs `--save-path`.
+ Purpose: runs `temperature_forecast.py` (7/1). Kind: CLI/shell wrapper.
+ Out: `../../results/weather/temperature_forecast_in7_out1/...`. Destination: `cli/baseline_repro/weather_temperature_forecast.sh`.

#### `evaluation/weather/run_indicator_prediction.sh`
+ **Replaced in step 14** by `cli/eval/weather_indicator.sh`: a dry run is the default (no model call), `--real` calls the model and needs `--save-path`; `--mode`, `--in-days` and `--out-days` are flags.
+ Purpose: runs `indicator_prediction.py` (7/1). Kind: CLI/shell wrapper.
+ Out: `../../results/weather/indicator_prediction_in7_out1/...`. Destination: `cli/baseline_repro/weather_indicator_prediction.sh`.

#### `evaluation/weather/run_question_answering.sh`
+ **Replaced in step 9** by `cli/eval/weather_mcqa.sh`: a dry run is the default (no model call, no cost), `--real` calls the model and needs `--save-path`.
+ Purpose: runs `mcqa.py` with `SETTING` long/short. Kind: CLI/shell wrapper.
+ Data: `../../data/processed/weather/QA${SETTING}`; out: `../../results/weather/question_answering_${SETTING}/<model>`.
+ Destination: `cli/baseline_repro/weather_question_answering.sh`.

## Cross-cutting sections

### 1. Dependency summary (for step 4)

Third-party packages actually imported (from `ast`), grouped by use:

| Use | Packages (import name -> PyPI name) |
| --- | --- |
| Finance prep | `numpy`, `pandas`, `matplotlib` |
| Weather prep | `numpy`, `pandas`, `tqdm` (`sklearn.metrics` imported but unused) |
| Evaluation | `numpy`, `matplotlib`, `sklearn` -> `scikit-learn` |
| Model APIs | `openai` (also DeepSeek via siliconflow base URL), `anthropic`, `google.generativeai` (see below) |
| Local Llama (lazy) | `torch`, `transformers`; implicitly `accelerate` for `device_map="auto"` |
| Downloads | `huggingface_hub` -> `huggingface-hub` |

Versus `requirement.txt`:

+ Never imported: `gdown`, `google` (unrelated PyPI package), `google-auth` (only a transitive dependency), the stdlib
  names `pathlib`, `json`, `datetime`, `argparse`, `re`.
+ Imported but missing: `tqdm`, `google-generativeai` (`import google.generativeai`). The code *uses* the `google-genai`
  API (`genai.Client`), which is listed, so the import line should become `from google import genai` and
  `google-generativeai` should not be added.
+ Needed at runtime but listed nowhere: `accelerate` (Llama path), HF token for the gated Llama weights.
+ Decided environment (applied to `pyproject.toml` / `uv.lock`): Python `>=3.12,<3.14`; `torch` stays a core dependency
  (template default, cu124 index); core also gains `numpy`, `scikit-learn`, `tqdm`, `huggingface-hub`; the optional extra
  `model` (`uv sync --extra model`) holds `transformers`, `accelerate`, `openai`, `anthropic`, `google-genai`.
+ Resolved versions are far newer than the originals (`openai` 1.59 -> 3.x, `anthropic` 0.43 -> 2.x, `google-genai` 1.2 ->
  2.x, `transformers` -> 5.x, `huggingface-hub` 0.29 -> 2.x); `api_call.py` has not been tested against them.
+ Version jumps: pandas 1.5.3 -> >=3.1 (copy-on-write, `.loc` setting on slices), numpy 1.24 -> 2.x, Python 3.10 ->
  >=3.12 (the 3.12 syntax above), matplotlib 3.9 -> 3.11.

### 2. Duplication between finance and weather (and within each)

| Duplicate | Where | Shared home |
| --- | --- | --- |
| Model-dispatch `if/elif` ladder (~12 lines) | all 9 eval entry points | `models/api.py` registry |
| Llama pipeline construction | 7 eval scripts | `models/api.py` |
| Dataset loader (glob `*.json`, pull fields) | all 9 eval entry points | `eval/data.py` |
| 20-sample checkpoint + `results.json` + `final_results.json` | all 9 | `eval/runner.py` |
| MCQA eval | `finance/mcqa.py` vs `weather/mcqa.py` (differ in prompt builder, schema, setting) | one runner + prompt fn |
| Forecast eval + interpolation + MSE-failure filtering | `finance/value_prediction.py` vs `weather/temperature_forecast.py` | `eval/forecast.py` |
| Trend/accuracy loop | `finance/trend_classification.py` vs `weather/trend_classification.py` | `eval/classify.py` |
| `timeseries_only`/`text_only`/`combined` branch in prompts | 3 finance + 3 weather prompt builders | one `compose_context(mode, ...)` helper |
| MACD vs BB vs price prompts | finance `*_metaprompt_generation` (3 near-copies) | one parameterised builder |
| `finance/correlation_prediction.py` vs `finance/mcqa.py` | ~90% identical | one runner |
| JSON helpers | `finance/utils.save_dict_to_local_json`, `read_json_from_local` vs `evaluation/utils.save_to_json` | `utils/io.py` |
| Window slicing | finance `sample_a_stock_pair...` vs weather `extract_temperature_data` + `interpolate_temperature_data` | `data/windows.py` (generic: event time, in/out window, granularity) |
| Prediction plots | `finance/utils.plot_timeseries_with_reference` vs `evaluation/utils.plot_series` | `utils/plot.py` |

### 3. Call graph

```text
download_raw_dataset.py          -> HF -> data/raw/{finance,weather}/...   (writes data/raw)
download_processed_dataset.py    -> HF -> data/processed/{finance,weather}/...

data_preparation/finance/run_create_pairs.sh -> create_pairs.py -> utils.py
data_preparation/finance/run_create_correlation.sh -> create_correlation.py (empty)
data_preparation/finance/run_create_mcqa.sh        -> create_mcqa.py        (empty)
data_preparation/weather/create_pairs.py            (no wrapper)

evaluation/finance/run_trend_classification.sh   -> trend_classification.py
evaluation/finance/run_ts_forecast.sh            -> value_prediction.py --indicator time
evaluation/finance/run_indicator_prediction.sh   -> value_prediction.py --indicator macd
evaluation/finance/run_question_answering.sh     -> correlation_prediction.py, mcqa.py
evaluation/weather/run_trend_classification.sh   -> trend_classification.py
evaluation/weather/run_temperature_forecast.sh   -> temperature_forecast.py
evaluation/weather/run_indicator_prediction.sh   -> indicator_prediction.py
evaluation/weather/run_question_answering.sh     -> mcqa.py

every evaluation/<domain>/*.py -> <domain>/meta_prompt.py (same dir)
                               -> evaluation/utils.py   (via sys.path "../..")
                               -> evaluation/api_call.py (via sys.path "../..")
data_preparation/finance/create_pairs.py -> data_preparation/finance/utils.py (same dir)
```

Leaf modules (no intra-repo imports): `evaluation/api_call.py`, `evaluation/utils.py`, both `meta_prompt.py`,
`data_preparation/finance/utils.py`, `data_preparation/weather/create_pairs.py`.

### 4. Suggested port order (each step leaves the repo working)

Status after step 16: all 40 original files are accounted for: 26 are ported or replaced and 14 are dropped or dead
(`.gitignore`, `README.md`, `requirement.txt`, 6 assets, `evaluation/weather/__init__.py`, the two empty `create_*` scripts
and their wrappers). Open items that are not file ports: the generic window sampler and the time-zone fix (item 6 below),
checking the ported data preparation against the downloaded data, and `docs/models.md`.

1. `eval/metrics.py` from `evaluation/utils.py` (pure numpy/sklearn functions) + tests with synthetic inputs.
   **Done in step 5** (metric functions only; `format_time_difference`, `save_to_json`, `plot_series` remain).
2. Finance numerics from `finance/utils.py`: `compute_sma/ema/macd/bollinger`, `calculate_stock_trend`,
   `to_timedelta`, sentiment mapping + tests. No data needed. **Done in step 6.**
3. Prompt builders and response parsers (both domains) as pure string functions + golden-string tests; collapse the
   mode-branch duplication here.
   **Done in step 7** (weather mode block merged; finance builders kept separate because their wording differs).
4. Weather prep helpers (`remove_duplicate_sentences`, `extract_temperature_data`, `interpolate_temperature_data`) +
   tests on synthetic frames (also validates the pandas 3 behaviour). **Done in step 6.**
5. `models/api.py` (env-var keys, registry, uniform `str` return) + mocked tests. **Done in step 8.**
6. Generic window sampler (`data/windows.py`) replacing the finance sampler; fix the timezone handling here.
7. Shared eval runner/loader; port one task end to end (weather MCQA is the smallest) against a handful of
   hand-made fixture JSONs. **Done in step 9.**
8. Remaining eval tasks and `cli/baseline_repro/*.sh`. **Done in steps 10 to 16** (the wrappers are under `cli/eval/`, not `cli/baseline_repro/`).
9. Download scripts (`scripts/`; only on explicit user request for `data/raw`). **Done in step 6.**
10. Prep entry points (`prepare_finance_pairs.py`, `prepare_weather_pairs.py`), validated against downloaded processed data. **Done in step 6** (validated on synthetic data only).
11. `docs/datasets.md` and `docs/models.md` from the README and the schemas observed. **`docs/datasets.md` drafted in
    step 6; `docs/models.md` is still open.**

### 5. Risks

1. **Data and generators are missing.** `data/` is empty locally. `create_correlation.py` and `create_mcqa.py` are empty,
   so the finance QA/correlation sets (and the GPT-4o annotation prompts behind them) cannot be regenerated, only
   downloaded. The weather prep script does not produce the QA files, the raw-to-`_processed.json` step is absent, and
   the long finance wrapper config is absent. Finance `create_pairs.py` appears to skip every article (see its entry), so
   it cannot be trusted to reproduce the HF data.
2. **Hardcoded paths and credentials.** Everything is cwd-relative (`../../data/...`, `../../results/...`,
   `sys.path.append("../..")`), defaults point at `/home/ubuntu/time/...`, API keys are in-source empty constants, and
   `setting` is derived by exact string match on a path. Downloads write `./data/raw`, which AGENTS.md forbids without
   an explicit request.
3. **API and environment drift.** Provider code is partly broken (`google.generativeai` vs `genai.Client`, `r1` return
   type, retired model ids, 30 s timeouts), the Llama weights are gated, and a full baseline run is costly (about
   20,000 finance and 2,000 weather samples times models times modes). Python 3.12-only syntax, pandas 1.5 -> 3, and a
   timezone-dependent timestamp scheme mean results will not match the paper without deliberate fixes.
4. Methodology details that affect comparability: outlier filtering by MSE threshold, silently dropped failed samples,
   unseeded sampling at temperature 0.7, and prompt text that misdescribes the short setting.

## Decisions and open items

+ Decided: Python >=3.12; `torch` core; `transformers`, `accelerate`, `openai`, `anthropic`, `google-genai` in the `model`
  extra.
+ HF dataset IDs were checked on 2026-11-01: all 12 `afeng/MTBench_*` IDs resolve. 11 redirect to
  `GGLabYale/MTBench_*`; `afeng/MTBench_weather_news` has not moved. Use the `GGLabYale/` IDs when porting the download
  scripts, keeping `afeng/` for that one dataset.
