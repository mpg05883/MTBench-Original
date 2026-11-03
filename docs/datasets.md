# Datasets

Draft written in step 6 of the refactor. It describes what the ported download and preparation code does. Anything that
could not be confirmed (only three small datasets were downloaded, into a temporary folder) is marked **TODO**.

Original code: <https://github.com/Graph-and-Geometric-Learning/MTBench>, pinned commit
`394a9d274403e93a08b24c2a0b7af461615ce302` (see `docs/provenance.md` for the file-by-file mapping).

## Sources

All datasets are hosted on the Hugging Face Hub under `afeng/MTBench_*`, the ids the download scripts in
`scripts/download/` use. On 2026-11-01 eleven of the twelve redirect to `GGLabYale/MTBench_*`;
`afeng/MTBench_weather_news` has not moved.

| Name | Hub repo | Local folder under `data/` |
| --- | --- | --- |
| `finance_news` | `afeng/MTBench_finance_news` | `raw/finance/news_articles` |
| `finance_stock` | `afeng/MTBench_finance_stock` | `raw/finance/stock_ohlcv` |
| `weather_news` | `afeng/MTBench_weather_news` | `raw/weather/event_reports` |
| `weather_temperature` | `afeng/MTBench_weather_temperature` | `raw/weather/temperature` |
| `finance_aligned_short` | `afeng/MTBench_finance_aligned_pairs_short` | `processed/finance/aligned_in7days_out1days` |
| `finance_aligned_long` | `afeng/MTBench_finance_aligned_pairs_long` | `processed/finance/aligned_in30days_out7days` |
| `finance_qa_short` | `afeng/MTBench_finance_QA_short` | `processed/finance/QAshort` |
| `finance_qa_long` | `afeng/MTBench_finance_QA_long` | `processed/finance/QAlong` |
| `weather_aligned_short` | `afeng/MTBench_weather_aligned_pairs_short` | `processed/weather/aligned_in7days_out1days` |
| `weather_aligned_long` | `afeng/MTBench_weather_aligned_pairs_long` | `processed/weather/aligned_in14days_out3days` |
| `weather_qa_short` | `afeng/MTBench_weather_QA_short` | `processed/weather/QAshort` |
| `weather_qa_long` | `afeng/MTBench_weather_QA_long` | `processed/weather/QAlong` |

Version: the original repo's README describes about 20,000 finance news articles and about 2,000 weather pairs from 50
stations. The Hub revisions checked on 2026-11-01 are listed under "Hub data formats"; no licence is named on the cards.

Domains (from the original README, not verified against the data):

- Finance: news (MarketWatch, Seeking Alpha, Zacks, Benzinga, ...) paired with the price series of the article's ticker.
  Short: 7 days of 5-minute prices in, 1 day out. Long: 30 days of hourly prices in, 7 days out.
- Weather: hourly GHCN-H observations (2003-2020) paired with NOAA Storm Events reports. Short: 7 days in, 1 day out.
  Long: 14 days in, 3 days out.

## How `data/` gets populated

`data/` is gitignored (the rule is `/data/`, so `src/mtbench/data/` is tracked). Processed and raw datasets are downloaded by separate launchers, each wrapping a script in `scripts/download/` that
uses `snapshot_download` into `data/processed/` or `data/raw/`:

```bash
./cli/download/processed_mtbench.sh   # the eight processed datasets, into data/processed/
./cli/download/raw_mtbench.sh         # raw data: only when you mean to write data/raw
```

The launchers retry each dataset with exponential backoff and need `uv sync --extra download`. The Python scripts
(`scripts/download/processed_mtbench.py`, `scripts/download/raw_mtbench.py`) take no arguments and write under
`resolve_data_dir()` from `mtbench.utils.path`. The launchers read `HF_TOKEN` from `.env` if it is set; none of these
datasets needed a token when checked.

## Preprocessing (what the ported code does)

The prepared pairs on the Hub were produced by the original authors' pipeline. The ported scripts reproduce the visible
part of it; the preparation outputs are written to an explicit output folder, never to `data/` by default.

### Finance pairs: `scripts/data/prepare_finance_pairs.py`, `cli/data/finance_pairs.sh`

Library: `mtbench.data.finance` (`pairs.build_pairs`).

1. Read the labelled news and one `<TICKER>.json` price series per ticker (`real_timestamp` in ms, `open` prices).
2. Shuffle the articles with seed 42 (`random` and `numpy` are both seeded).
3. For every ticker of an article, cut an input window before the publication time and an output window from it
   (`windows.sample_a_stock_pair_flexible_units_given_event`; the series is assumed to be 5-minute bars).
4. Add trend labels from the window means: percentage change of the output mean over its first price, binned at
   -4, -2, +2, +4 percent into `<-4%`, `-2% ~ -4%`, `-2% ~ +2%`, `+2% ~ +4%`, `>+4%` (`trend.TREND_BINS`).
5. Add technical indicators for the input, output and combined window (SMA and EMA 10/50/200, MACD, signal, Bollinger
   bands), named `in_*`, `out_*`, `overall_*`.
6. Add `alignment`: `consistent` if the output trend's sentiment (negative, neutral or positive) appears among the
   sentiments of the article's labels, else `inconsistent`.
7. Save `<index>_<ticker>.json` and a plot in `visualization/`.

Settings: short = 7 days / 5 minutes in, 1 day / 5 minutes out (from the original `run_create_pairs.sh`). The long
setting in the wrapper (30 days / 1 hour in, 7 days / 1 hour out) comes from the README; the original repo has no script
for it.

### Weather pairs: `scripts/data/prepare_weather_pairs.py`, `cli/data/weather_pairs.sh`

Library: `mtbench.data.weather.pairs` (`generate_pairs`).

1. Per station, read `news_<id>.json` and `<id>_processed.json`.
2. Remove repeated sentences from each report and keep the `top_number` longest (40 by default).
3. For each report, take the `days_before` calendar days up to the report's end date as input and the `days_after`
   following days as output (default 14 and 3).
4. Resample each window to exactly `days * 24` hourly points: missing hours are interpolated linearly in time and the
   ends are filled forward, then backward.
5. Save `<output>/<before>_<after>/<top_number>/<station>/<i>.json`.

## Hub data formats (checked 2026-11-01)

What the Hub holds, from the dataset-viewer schemas and dataset cards for all twelve datasets, and from downloading three
of them (`finance_qa_short`, `weather_qa_short`, `weather_aligned_short`, 45 MB, into a temporary folder; no model was
called). Revisions are the Hub commit hashes (first 10 characters); the cards name no licence.

| Name | Revision | Format | Size / rows |
| --- | --- | --- | --- |
| `finance_news` | bfc2f582fd | one parquet file; columns include `content`, `tickers` (list), `published_utc` (timestamp without `Z`), `label_type`, `label_time`, `label_sentiment` | 55 MB |
| `finance_stock` | 0c1a656a96 | parquet shards, one row per stock with list columns (`timestamp`, `open`, `high`, `low`, `close`, `volume`, `vwap`, `transactions`, `otc`, `real_timestamp`); the viewer shows no ticker column | 16.5 GB |
| `weather_news` | efd9b70c84 | 50 JSON files `news_<station>.json` | 56 MB |
| `weather_temperature` | 7c112fcc40 | parquet, 49 rows (one per station) with list columns (`DATE`, `temperature`, `dew_point_temperature`, ...); the viewer shows no station column | 168 MB |
| `finance_aligned_short` / `_long` | 5e30441d1c / a1bcb7eda5 | one parquet file each; columns `input_timestamps`, `input_window`, `output_timestamps`, `output_window`, and `text`, `trend`, `technical`, `alignment` as strings (JSON-encoded for the first three) | 750 rows (the card says 2,000); 88 MB / 23 MB |
| `finance_qa_short` / `_long` | a0c6ce4100 / 1e0cb72462 | one JSON file per sample, `<index>_<TICKER>.json` | 491 files, 13 MB / about 7.6 MB |
| `weather_aligned_short` / `_long` | 953a48f27d / 7c366de2ed | one JSON file per sample, `<station>_<i>.json`, plus a README | 1,959 files, 33 MB / 34 MB |
| `weather_qa_short` / `_long` | cd5471e60a / fc8099ec82 | one JSON file per sample, `<station>_<i>.json`, plus a README | 645 files, 11 MB / 16 MB |

Downloaded samples (these match what the ported evaluation code reads):

- Finance QA: `input_timestamps`, `input_window` (390 values for most samples, 312 or 354 for some: 5 trading days of 78
  five-minute bars), `output_timestamps`, `output_window` (78 values), `text` (the article), `timestamp_ms`,
  `published_utc` (with a trailing `Z`), `article_url`, `news_price_correlation` and `MCQA` (`question`, `answer`). The
  491 files hold 94 / 150 / 36 / 103 / 108 samples of Strong Positive / Moderate Positive / No / Moderate Negative /
  Strong Negative correlation, and answers A / B / C / D 127 / 137 / 115 / 112 times.
- Weather QA: `text`, `input_timestamps` and `input_window` (168 values), `output_timestamps` and `output_window` (24),
  `question`, `answer` (A 125, B 276, C 171, D 73 samples).
- Weather aligned pairs: the same without a question, plus a `hasrain` flag.

Checked on these real samples: the ported finance multiple-choice and correlation tasks, and the weather multiple-choice,
trend (past and future), indicator and forecast tasks, run through their loaders, prompts and parsers on the first 30
samples of each folder with a fake model, with no loading or prompt errors (the only failures were weather forecasts
above the error threshold, from a constant fake forecast).

## Splits

All the Hub datasets have a single `train` split; there is no held-out split. No split is defined in the original
code or in the ported code. The pairs are evaluation data: models are prompted, not trained, in the ported tasks.
**TODO:** if training or tuning is added, define a split (by station or by article, never by row) and record its function
and seed here (AGENTS.md asks for this).

### Parity subsets (evaluation only, not a split)

The refactor evaluation parity experiment evaluates a fixed 300-item subset of each of its 22 cells. They are drawn by
`scripts/data/make_parity_subsets.py` with `mtbench.eval.subsets` (`sample_by_label`, `sample_by_change`), seed 42 (one
`random.Random` per draw, seeded `"<seed>:<draw>"`), and saved as `experiments/2026-11-02_refactor_evaluation_parity/
subsets/<cell>.json` (file names) with a `manifest.json` of population and sampled counts per stratum.

- Trend, correlation, MCQA: stratified by label, proportional, at least 10 per label where the set has that many.
- Forecast and weather indicator: terciles of the absolute change between the last input value and the target mean,
  spread over stations with no station above 5% of a cell. The finance forecast cells (`time`, `macd`, `bb`) share one
  draw, based on the price series. The converted finance pairs have no ticker, so they are not grouped.
- A set of at most 300 usable items is taken whole. The subsets are for the parity check only; never tune on them.
- Not yet run on the real data (the data was not downloaded when this was written); counts are unverified.

## Known issues in the original (kept as-is)

- Finance pairs through the script: `read_folder_of_json` returns `{file_name, data}` items, but the loop looks for
  `content` and `tickers` on the wrapper, so every article is skipped and no pairs are written.
- Window timestamps depend on the machine's time zone (naive UTC datetimes read as local time).
- `calculate_stock_trend` gives a float `nan` instead of a label when the percentage change is NaN; callers must check
  the type.
- The pair index counts failed tickers, so file numbers can have gaps.
- The weather script is named `create_pairs` and its function `generate_QA_data`, but it makes aligned pairs, not
  question-answer data.

## Gaps found by the check

- **Finance aligned pairs are parquet, not per-sample JSON.** `finance_trend` and `finance_forecast` read one JSON file
  per sample with `text` as a dict (`content`, `timestamp_ms`), and `trend` and `technical` as dicts. The Hub files hold
  those three as JSON-encoded strings in one parquet table. Checked by downloading `finance_aligned_long` (23 MB): 525
  rows (the card says 2,000), 137 input and 33 output points per row, `text` with `article_url`, `content`,
  `label_sentiment`, `label_time`, `label_type`, `published_utc` and `timestamp_ms`, `trend` with the six change and bin
  fields, `technical` with the 30 indicator series, and `alignment` as the JSON string `"consistent"` or
  `"inconsistent"` (431 and 94 rows). Output labels: 32 `<-4%`, 33 `-2% ~ -4%`, 204 `-2% ~ +2%`, 157 `+2% ~ +4%`, 99
  `>+4%`. **No row has a ticker**, so the `<index>_<TICKER>.json` names cannot be rebuilt; the two finance tasks only use
  the integer before the underscore. A throwaway conversion in the scratch folder (decode the three strings, write
  `<row>_pair.json`) lets `finance_trend` and `finance_forecast` (`time`, `macd`, `bb`) run on the first 40 real rows
  with a fake model and no loading or prompt errors (the forecast failures are error-threshold exclusions from a
  constant fake forecast). Reading parquet needs a parquet engine (pyarrow), which the project does not depend on yet.
  The short set (750 rows, 88 MB) was not downloaded. The finance QA sets and the weather sets are already per-sample
  JSON and work as they are.

  **Converter (step 17):** `mtbench.data.finance.parquet.convert_aligned_pairs` and `scripts/data/convert_finance_parquet.py`
  decode the table into one file per row (`<row>_pair.json`, the same keys in the same order as the original pair files,
  `NaN` kept). It reads the downloaded dataset folder and writes to a folder you choose; pyarrow is in the `download`
  extra. Run on the real `finance_aligned_long` table it wrote 525 files, and the trend and forecast tasks read them:

  ```bash
  ./cli/download/processed_mtbench.sh
  uv run python scripts/data/convert_finance_parquet.py --setting long --output-dir <converted folder>
  ./cli/eval/finance_trend.sh --dataset-folder <converted folder> --max-samples 5
  ```

- **The raw data cannot be turned into the preparation scripts' input from the Hub copies alone.** Checked by downloading
  one file of each raw set (about 125 MB, into a temporary folder):
  - `finance_stock` (shard 281, 3 rows): each row is one stock's whole 5-minute series (about 191,000 bars,
    `real_timestamp` in milliseconds, 300,000 ms apart) with the columns `timestamp`, `open`, `high`, `low`, `close`,
    `volume`, `vwap`, `transactions`, `otc`, `real_timestamp`. **There is no ticker anywhere**, in the table or in
    `metadata.jsonld`, so the `<TICKER>.json` files that `prepare_finance_pairs` reads cannot be built.
  - `finance_news` (20,000 articles, one parquet file): exactly one ticker per article; `published_utc` is a timestamp
    (a datetime), not the `%Y-%m-%dT%H:%M:%SZ` string that `convert_iso8601_to_datetime_and_timestamp` requires; the
    labels are lists. A converter could write per-article JSON with the date formatted back, but the articles' tickers
    would find no series (see above).
  - `weather_temperature` (shard 1, 16 of the 49 rows): each row is one station's series from 2003-01-01 to 2024 (about
    280,000 readings with irregular times such as `00:51:00`) with 18 columns and **no station id**. The processed
    `<station>_processed.json` files that `prepare_weather_pairs` reads (hourly `DATE` and `temperature` records) are not
    on the Hub, and the step that makes them from these tables is not in the original repo.
  - `weather_news`: the only raw set that already matches a preparation script. `news_<station>.json` is a pandas
    column-oriented JSON object with `BEGIN_TIMESTAMP`, `END_TIMESTAMP` and `NEWS`, which `pd.read_json` in the weather
    script reads.

  So the ported preparation scripts cannot be run on the Hub copies, and their output cannot be compared with the Hub's
  aligned pairs, without a table that maps rows to tickers and stations (ask the dataset authors) and, for the weather
  data, the missing resampling step. The processed sets on the Hub are the practical starting point.
- **Counts differ from the cards:** the finance aligned pairs hold 750 rows, where the card says 2,000; the finance QA
  set has 491 files, where the card says 490.

## TODO: unconfirmed

- Ask the dataset authors for the ticker of each stock row and the station of each weather row, and for the step that
  makes the hourly `<station>_processed.json` files.
- Run the converter on the short set (`finance_aligned_short`, 750 rows) to confirm the same columns.
- How the processed aligned pairs, the QA sets and the correlation labels were generated: `create_mcqa.py` and
  `create_correlation.py` are empty upstream, and the weather QA step is not in the repo.
- How synthetic reports for stations without a narrative were made (mentioned in the README, not in the code).
- Whether the ported scripts reproduce the Hub's aligned pairs; this needs the raw data and a comparison run.
- Results on pandas 1.5 versus pandas 3.1 (the parity tests ran the original on pandas 3.1 only).
- Licences: the dataset cards name none.

## Candidate data sources for expansion (under evaluation)

All sources below are candidates. None has yet been downloaded, aligned, or evaluated. Access points are the providers
and routes believed to hold each source; exact endpoints, coverage dates, and license terms are unverified.

### Motivation

The current benchmark covers two domains (finance, weather) and has known limitations:

- Narrow domain coverage.
- Modality necessity is unproven: many QA items are text-dominant.
- Alignment relies on heuristics (e.g., a 50 km station radius, article-position anchoring) with no sensitivity
  analysis.
- Part of the text is LLM-generated or LLM-annotated (synthetic weather narratives, GPT-4o finance labels) with no
  powered human audit.
- Contamination risk: identifier masking does not rule out memorized articles or events.

### Selection principle

Sources are chosen so that the text is human-written, carries information the TS history alone cannot contain, and has
a deterministic alignment key. Most are official US government sources, which avoids LLM annotation and allows a
post-cutoff (2025-2026) split for contamination checks.

### Common pair structure

Each example has an input window of TS history ending at time *t*, a text document issued at or before *t*, and a
target consisting of TS behavior after *t*. Alignment is justified on three axes:

- **Entity:** the text is about the thing the TS measures.
- **Time:** the text and input window contain no information from after *t*.
- **Relevance:** the text addresses the target's horizon.

### Recurring hazards

- Forecast-type text may contain the target values, so a model can copy instead of reason.
- Revised data or retrospective text can leak future information.
- Sparse-alert sources need matched no-alert control windows, or a model can learn "alert exists means event."

### Group A: Expert forward-looking rationale

#### A1. Normal weather: NWS Area Forecast Discussions + GHCN-H

**What it is.**

- **TS:** Hourly airport station observations: temperature, dew point, wind, precipitation, pressure. Same family as
  the existing weather data.
- **Text:** Area Forecast Discussions (AFDs), informal technical memos written by meteorologists at each of the 122 NWS
  Weather Forecast Offices several times a day. They explain the reasoning behind the official forecast (approaching
  systems, model trust, confidence), organized by horizon out to about 7 days.
- **Why text adds signal:** Forecasters see radar, satellite, and model output showing systems that a station's own
  history cannot reveal.

**Where to access (unverified).** AFD archive via the Iowa Environmental Mesonet text-product archive; office
coverage-area boundaries from NWS shapefiles; station observations from NOAA NCEI (GHCN-H).

**Alignment.**

- **Entity:** Station mapped to the forecast office whose area contains it (deterministic spatial lookup; replaces the
  50 km heuristic).
- **Time:** AFD issue time ends the input window; section headers (e.g., "Saturday through Wednesday") give the
  horizon.
- **Relevance:** Text forecasts the same variables for the surrounding region.

**Watch out for.**

- The AFD covers a region, so regional statements may not match a single airport.
- AFDs contain numeric forecasts, creating a copying risk.
- Outcomes are observable, so each pair can later be labeled forecaster-right or forecaster-wrong without LLMs.

#### A2. Cyclones: NHC Tropical Cyclone Discussions + HURDAT2

**What it is.**

- **TS:** HURDAT2 "best track": storm latitude/longitude, maximum sustained wind, and minimum central pressure every 6
  hours (00, 06, 12, 18 UTC). Intensity is hard to forecast, especially rapid intensification (about a 30-knot jump in
  24 hours).
- **Text:** Forecaster discussions issued with each advisory for every active storm. They explain expected track and
  intensity with reasoning (wind shear, sea surface temperature, model disagreement) and include a forecast table out
  to 5 days.
- **Why text adds signal:** It carries reasoning about conditions ahead of the storm that the storm's own track history
  cannot show.

**Where to access (unverified).** NHC archives and data directory (HURDAT2 best track, advisory archives); text
products may also be archived by the Iowa Environmental Mesonet.

**Alignment.**

- **Entity:** Storm ID (e.g., AL092022), identical in both sources.
- **Time:** Discussions are issued at about 03/09/15/21 UTC, roughly three hours after the 00/06/12/18 UTC observation
  time they describe. The input window ends at the best-track point the discussion is based on; the target is the
  points after it.
- **Relevance:** Text concerns that storm's future wind, pressure, and position.

**Watch out for.**

- HURDAT2 is revised after the season, so it is the official truth but not exactly what the forecaster saw.
- Only about 15 to 20 Atlantic storms per year, and consecutive 6-hour points within a storm are highly correlated;
  train/test splits should be by storm.
- The forecast table contains the answer.
- Natural conflict cases exist (forecast says weakening, storm rapidly intensifies).

#### A3. Geomagnetic activity: NOAA SWPC Forecast Discussion + Kp index

**What it is.**

- **TS:** The Kp index, a global 0-9 score of how disturbed Earth's magnetic field is, computed every 3 hours. The scale
  is roughly logarithmic, and Kp >= 5 counts as a geomagnetic storm. It is one global series.
- **Text:** Space Weather Prediction Center (SWPC) forecast discussions: forecaster summaries of recent solar activity
  (coronal mass ejections, coronal holes) and the expected disturbance over the next 3 days.
- **Why text adds signal:** A coronal mass ejection takes 1 to 4 days to reach Earth and is visible in solar imagery the
  whole way, while Kp stays flat until arrival. This is the cleanest leading-indicator case in the list.

**Where to access (unverified).** NOAA SWPC forecast products and archives for the text; Kp from NOAA SWPC or GFZ
Potsdam. The archive format of the historical text forecasts is the main unknown.

**Alignment.**

- **Entity:** None needed (global index), which isolates temporal alignment from entity matching.
- **Time:** Issue time ends the input window; the 3-day forecast maps onto 24 three-hour bins. The time zone used for
  "days" in the text must be confirmed as UTC.
- **Relevance:** The text is explicitly about the target quantity.

**Watch out for.**

- The text includes a numeric Kp forecast table, so copying is possible.
- Storms are rare, so classes are imbalanced, and activity varies with the 11-year solar cycle.
- Consecutive daily discussions are near-duplicates.
- The text may mention Kp values directly.

### Group B: Leading indicators with a lag

#### B1. Floods: NWS Flood Warnings/Statements + USGS river gauges

**What it is.**

- **TS:** River gauge **stage** (height of the water surface above a fixed reference) and **discharge** (volume passing
  per second), recorded every 15 minutes at thousands of USGS sites. Each location has a flood stage above which damage
  begins (minor, moderate, major categories).
- **Text:** NWS Flood Warnings and Flood Statements describing upstream rain, soil saturation, and predicted crest
  (e.g., "will crest near 24.5 feet Thursday morning").
- **Why text adds signal:** River flooding is lagged: rain falls upstream and reaches downstream points hours to days
  later. The warning precedes the rise, so gauge history alone cannot anticipate it. This also tests causal-delay
  reasoning.

**Where to access (unverified).** Warning and statement products via the Iowa Environmental Mesonet archive; stage and
discharge via the USGS National Water Information System (NWIS) web services; NWS forecast-point identifiers for the
gauge crosswalk.

**Alignment.**

- **Entity:** The river and forecast point named in the warning is crosswalked to a USGS gauge number. Many NWS forecast
  points sit at USGS gauges. When the text discusses upstream conditions, watershed topology (which gauges are upstream
  or downstream of which) identifies the downstream gauges the text implies.
- **Time:** Warning issue time ends the input window; the predicted crest time sets the horizon.
- **Relevance:** Text is about that river's stage.

**Watch out for.**

- Only warnings and statements are valid inputs. Storm Events Database entries are written after the event and would
  leak the outcome.
- Crosswalk errors, dam and reservoir regulation, and warnings covering several gauges.
- Predicted crest numbers in the text.
- Flash floods (hours, small streams) and river floods (days) are different regimes.

#### B2. Energy markets and grid operations

**What it is.**

- **TS:** Hourly demand, generation, and interchange per balancing authority (BA, the operator that matches supply and
  demand in a region, e.g., ERCOT, CAISO, PJM) from EIA-930; monthly prices and stock levels from EIA; real-time
  wholesale prices from the grid operators. Prices can spike by roughly 100x in a crisis (e.g., Winter Storm Uri).
- **Text:** EIA Short-Term Energy Outlook (monthly narrative on oil, gas, electricity); Energy Emergency Alerts (levels
  1 to 3, with 3 meaning load shedding is imminent or underway); CAISO Flex Alerts (public conservation requests); DOE
  OE-417 outage and disturbance reports.
- **Why text adds signal:** Alerts name the physical cause (generator failures, cold snaps, fuel shortages) behind price
  spikes. "Busted" alerts, where a warning was issued and no outage followed, are built-in conflict cases.

**Where to access (unverified).** EIA API v2 (free key) for EIA-930 and the Short-Term Energy Outlook; alerts published
separately by each grid operator; DOE OE-417 reports. Alerts are scattered across many sites and formats.

**Alignment.**

- **Entity:** Balancing authority ID. Alerts come from the BA, so matching is clean; OE-417 is reported by utility or
  state and maps to a BA less cleanly.
- **Time:** Alert timestamp ends the input window; the stated affected hours set the horizon.
- **Relevance:** Operational alerts concern the same region's supply and demand.

**Watch out for.**

- Alerts are sparse and cluster around crises; sampling only windows with alerts teaches "alert exists means spike," so
  matched no-alert control windows are needed.
- Alerts come from many operators in many formats.
- EIA-930 has known data-quality issues and needs cleaning.

#### B3. Aviation: ATCSCC advisories + airport operations

**What it is.**

- **TS:** Airport operational data in 15-minute bins: scheduled and actual arrivals and departures, taxi times, delays.
- **Text:** Advisories from the FAA Air Traffic Control System Command Center (ATCSCC) announcing ground stops (flights
  held at origin) and ground delay programs (departures assigned later times), with a stated cause and effective period
  (e.g., "Ground Delay Program at EWR effective 1500Z to 0300Z due to thunderstorms").
- **Why text adds signal:** Delay statistics show lateness only after it happens, while advisories announce future
  constraints and their cause.

**Where to access (unverified).** FAA ATCSCC advisory archive for the text; FAA ASPM for operational data. Whether ASPM
can be bulk-downloaded, and under what terms or registration, is unknown.

**Alignment.**

- **Entity:** Airport ICAO code (KLGA; the 3-letter form LGA is also common). Some advisories cover several airports
  (e.g., New York metro), so the mapping is one-to-many.
- **Time:** Advisory timestamp ends the input window, and the window must end before the stated effective period
  starts.
- **Relevance:** The advisory is about that airport's delays.

**Watch out for.**

- Advisories issued after delays begin mostly restate the TS.
- Programs canceled early when weather moved away are natural conflict cases.
- Matched no-advisory control windows are needed.

### Group C: Low-frequency explanatory text

#### C1. Macroeconomics: FOMC documents + observed macro series

**What it is.**

- **TS:** Observed series from FRED, accessed through ALFRED vintages (values as originally published): effective
  federal funds rate (daily), core PCE inflation and unemployment rate (monthly), and optionally real GDP growth
  (quarterly, heavily revised). Fed funds, inflation, and unemployment correspond to the Fed's policy instrument and its
  two mandates.
- **Text:** Documents from the Federal Open Market Committee (FOMC, which sets US short-term rates at 8 meetings per
  year):
  - Statements, released the same day as the meeting.
  - Minutes, released about three weeks after the meeting, with the detailed reasoning and disagreements.
  - Summary of Economic Projections (SEP) narrative, at the March, June, September, and December meetings.

  Each type is treated as a separate text condition.
- **Why text adds signal:** It explains why officials changed their views and what risks they weigh. Observed series are
  slow-moving, and turning points are what the text can anticipate.

**Where to access (unverified).** federalreserve.gov for statements, minutes, and SEP; FRED/ALFRED API (free key) for
observed series and vintages.

**Alignment.**

- **Entity:** A single national entity, so there is no matching problem; alignment is temporal and relevance-based.
- **Time:** The anchor is each document's public release date (for minutes, the release date, not the meeting date). The
  input window uses the ALFRED vintage as of that date. The target is realized values over the next 1 to 4 quarters
  under one stated revision rule: either the first release or a value fixed a set lag after the reference period.
- **Relevance:** Text discusses the outlook for the same variables, and can be checked per example for which variables
  and what direction (tightening, easing, risks tilted up or down).

**Design note.** An earlier design used the SEP projections as the TS. It was rejected because each release contains
only a handful of year-end values and the text restates them, making the task extraction. Observed series with realized
targets avoid this.

**Watch out for.**

- Small N: about 8 meetings per year, roughly 120 examples over 15 years, and about 60 for SEP only. Overlapping
  4-quarter targets make nearby examples dependent, so splits should be by time block.
- Few independent regimes (2008, 2020, 2022 dominate).
- Policy reflexivity: the text influences the outcome it describes, which complicates reading "conflict" cases as the
  text being wrong.
- Contamination: FOMC documents and macro history are widely known.
- The choice of revision rule changes the labels.

#### C2. Agriculture: USDA WASDE

**What it is.**

- **TS:** The USDA's monthly World Agricultural Supply and Demand Estimates for each major crop (corn, soybeans, wheat,
  rice, cotton): a balance sheet (beginning stocks + production + imports = exports + domestic use + ending stocks) plus
  expected farm price, per **marketing year** (a 12-month trading period; corn runs September to August, labeled e.g.
  "2025/26"). The TS is the sequence of monthly estimates, showing how USDA's belief evolves.
- **Text:** The report narrative per commodity explaining each revision (e.g., "production is lowered on reduced yields
  due to dry conditions").
- **Why text adds signal:** The numbers show that stocks were revised; only the text gives the cause (persistent drought
  versus a one-off trade shock), which implies momentum or reversal.

**Where to access (unverified).** USDA ESMIS archive (hosted at Cornell University Library) for historical reports.
Balance-sheet numbers are in tables or PDFs and require parsing.

**Alignment.**

- **Entity:** Commodity plus marketing year.
- **Time:** Text and TS are co-published, so the target must be later: the next month's revision, final ending stocks,
  or the realized farm price.
- **Relevance:** The text explains the latest revision visible in the TS.

**Watch out for.**

- Co-publication means the text describes a change already in the TS.
- Small N (12 reports per year), and commodities are correlated with each other.

#### C3. Healthcare: CDC FluView

**What it is.**

- **TS:** ILINet, the weekly percentage of outpatient visits for influenza-like illness (fever plus cough or sore
  throat), reported by clinics nationally, by region, and by state; plus laboratory positivity counts. Weeks follow the
  MMWR calendar (Sunday to Saturday); FluView is published on Fridays for the week ending the prior Saturday.
- **Text:** FluView's weekly narrative on activity levels, circulating subtypes (H1N1, H3N2, B), severity indicators
  (hospitalizations, pediatric deaths), and whether circulating strains match the vaccine.
- **Why text adds signal:** Case counts show outbreak size, while the text adds qualitative biology (dominant subtype,
  vaccine match) that affects severity and wave duration.

**Where to access (unverified).** CDC FluView; the CMU Delphi Epidata API, which may store historical issues (as-of
values). The narrative text is in weekly reports and requires parsing.

**Alignment.**

- **Entity:** National, region, or state, matched to the corresponding section of the report.
- **Time:** MMWR week key plus Friday publication date. The window ends at the week the report covers, and the target is
  the next 1 to 4 weeks.
- **Relevance:** The weakest of all the sources; the text largely narrates the TS numbers, and its link to future values
  is qualitative.

**Watch out for.**

- ILINet values are revised as late reports arrive, so as-of vintage data is needed.
- The 2020 to 2022 COVID period distorts seasonal patterns.

### Alignment strength (prior to evaluation)

- **Strongest:** A1, A2, A3, B1. The text is forward-looking and expert-written, the keys are deterministic, and
  outcomes are verifiable.
- **Medium:** B2, B3. The text is informative but sparse, and entity mapping is messier.
- **Weakest as designed:** C1, C2, C3. The text is co-published with or restates the TS, so these depend on the target
  redesigns described above.

### Planned validation protocol (all sources)

1. Deterministic checks: entity keys match, and no text or input timestamp falls after the anchor.
2. Stratified human audit (about 30 to 50 pairs per source): ratings of temporal alignment, entity match, relevance, and
   whether the text contains target information.
3. Shuffled-text control: text from a different time or entity is swapped in; if performance does not drop, alignment is
   not doing work.
4. Ablations: TS-only, text-only, and no-evidence baselines, plus a "both-necessary" subset where TS-only and text-only
   both fail.
5. Sensitivity of results to alignment parameters (anchor offset, spatial mapping), replacing unexamined heuristics.
6. A post-cutoff time-based split (2025 to 2026) to check contamination.
