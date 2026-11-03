"""Draw the fixed 300-item subsets of the refactor evaluation parity
experiment, one list of file names per cell.

This is a self-contained copy of scripts/data/make_parity_subsets.py of the
refactored MTBench repository (with the sampler of mtbench.eval.subsets inlined
and the sample readers rewritten after the evaluation scripts of this
repository), so that both repositories draw exactly the same files. Keep the
sampler functions in step with that repository: the seed, the random
generators and the tie breaking by file name decide which items are drawn.

The lists go to --output-dir (default subsets/ in the repository root) as
<cell>.json, with a manifest.json that holds, per cell, the seed, the
population and sampled counts per stratum (to reweight the strata to the full
set). Strata:
- finance trend, correlation and MCQA, weather trend and MCQA: the label,
    proportional with at least 10 items per label.
- forecasts and the weather indicator: terciles of the absolute change between
    the last input value and the mean of the target window, spread over the
    weather stations (no group above 5% of a cell). The three finance forecast
    cells use one draw and the price series for the change, so they share
    items.
    The converted finance pairs carry no ticker, so they are not grouped.

This only reads the data. The Hub ships the finance aligned pairs as a parquet
table, so they must first be converted to one JSON file per pair with
scripts/data/convert_finance_parquet.py of the refactored repository
(--finance-converted-dir holds the short/ and long/ outputs). Both
repositories must read the same converted folder, as the draws depend on the
file names. --dry-run prints the sizes without writing.

Run it from this repository:
    python evaluation/make_parity_subsets.py --finance-converted-dir <dir>
"""

import argparse
import json
import logging
import math
import random
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from utils import compute_temperature_trend

ROOT = Path(__file__).resolve().parent.parent
WEATHER_SETTINGS = (("short", 7, 1), ("long", 14, 3))
TERCILES = 3

logger = logging.getLogger(__name__)


@dataclass
class Subset:
    """A drawn subset.

    Attributes:
        names (list[str]): The chosen file names, sorted.
        population (dict[str, int]): Items per stratum in the full set.
        sampled (dict[str, int]): Items per stratum in the subset. Dividing
            the two gives the weights that undo the stratified sampling.
    """

    names: list[str] = field(default_factory=list)
    population: dict[str, int] = field(default_factory=dict)
    sampled: dict[str, int] = field(default_factory=dict)


def make_rng(seed: int, draw: str) -> random.Random:
    """Return a generator for one draw, so draws do not depend on each other.

    Args:
        seed (int): The experiment seed.
        draw (str): The draw's name, e.g. a cell name.

    Returns:
        random.Random: A generator seeded from both.
    """
    return random.Random(f"{seed}:{draw}")


def absolute_change(sample: Mapping[str, Any]) -> float | None:
    """Return the absolute change between the last input value and the mean
    of the target window.

    Args:
        sample (Mapping[str, Any]): A sample with `input_window` and
            `output_window`.

    Returns:
        float | None: The change, or None if a window is empty or not
            numeric.
    """
    try:
        last = float(sample["input_window"][-1])
        target = [float(v) for v in sample["output_window"]]
    except (TypeError, ValueError, IndexError, KeyError):
        return None
    if not target:
        return None
    change = abs(sum(target) / len(target) - last)
    return change if math.isfinite(change) else None


def allocate(
    counts: Mapping[str, int], n: int, floor: int = 0
) -> dict[str, int]:
    """Split `n` draws over strata in proportion to their sizes.

    Every stratum gets at least `min(floor, size)` and at most its size, and
    the result sums to `n`, with the largest remainders deciding the rest.

    Args:
        counts (Mapping[str, int]): Items per stratum.
        n (int): The number of draws; at most the total.
        floor (int): The minimum per stratum. Defaults to 0.

    Returns:
        dict[str, int]: Draws per stratum.

    Raises:
        ValueError: If `n` is more than the items, or the floors alone exceed
            `n`.
    """
    total = sum(counts.values())
    if n > total:
        raise ValueError(f"Cannot draw {n} from {total} items.")
    minimum = {c: min(floor, k) for c, k in counts.items()}
    if sum(minimum.values()) > n:
        raise ValueError(f"The floors need {sum(minimum.values())} > {n}.")
    ideal = {c: n * k / total for c, k in counts.items()}
    alloc = {
        c: min(counts[c], max(minimum[c], round(ideal[c]))) for c in counts
    }
    # Fix the rounding: add to the most under-served stratum, or take from the
    # most over-served one, one at a time (ties by name).
    while (diff := n - sum(alloc.values())) != 0:
        if diff > 0:
            open_ = [c for c in sorted(counts) if alloc[c] < counts[c]]
            pick = max(open_, key=lambda c: ideal[c] - alloc[c])
            alloc[pick] += 1
        else:
            open_ = [c for c in sorted(counts) if alloc[c] > minimum[c]]
            pick = min(open_, key=lambda c: ideal[c] - alloc[c])
            alloc[pick] -= 1
    return alloc


def sample_by_label(
    labels: Mapping[str, str],
    n: int,
    rng: random.Random,
    floor: int = 10,
) -> Subset:
    """Draw items stratified by label, proportional to the label frequencies
    with a minimum per label.

    Args:
        labels (Mapping[str, str]): The label of each file name.
        n (int): The subset size. A set of at most `n` items is taken whole.
        rng (random.Random): The generator.
        floor (int): The minimum per label where the set has that many.
            Defaults to 10.

    Returns:
        Subset: The names and the per-label counts.
    """
    by_label: dict[str, list[str]] = defaultdict(list)
    for name in sorted(labels):
        by_label[str(labels[name])].append(name)
    population = {c: len(v) for c, v in sorted(by_label.items())}
    if len(labels) <= n:
        return Subset(sorted(labels), population, dict(population))

    alloc = allocate(population, n, floor)
    chosen: list[str] = []
    for label in sorted(by_label):
        chosen += rng.sample(by_label[label], alloc[label])
    return Subset(sorted(chosen), population, alloc)


def sample_by_change(
    changes: Mapping[str, float],
    groups: Mapping[str, str] | None,
    n: int,
    rng: random.Random,
    max_share: float = 0.05,
) -> Subset:
    """Draw items spread over terciles of the absolute change and over groups.

    The terciles get equal shares. Inside a tercile the groups (stations or
    tickers) are cycled through so no group supplies more than `max_share` of
    the subset where enough groups exist; with fewer groups the cap is raised
    to the smallest feasible one.

    Args:
        changes (Mapping[str, float]): The absolute change of each file name.
        groups (Mapping[str, str] | None): The group of each file name, or
            None for no grouping.
        n (int): The subset size. A set of at most `n` items is taken whole.
        rng (random.Random): The generator.
        max_share (float): The largest share of the subset for one group.
            Defaults to 0.05.

    Returns:
        Subset: The names and the per-tercile counts.
    """
    ranked = sorted(changes, key=lambda name: (changes[name], name))
    tercile = {
        name: str(min(TERCILES - 1, rank * TERCILES // len(ranked)))
        for rank, name in enumerate(ranked)
    }
    population = dict(sorted(Counter(tercile.values()).items()))
    if len(ranked) <= n:
        return Subset(sorted(ranked), population, dict(population))

    group_of = groups or {}
    cap = max(1, int(max_share * n))
    n_groups = len({group_of.get(name, "") for name in ranked})
    if n_groups * cap < n:
        cap = math.ceil(n / n_groups)
        if groups is not None:
            logger.warning(
                "Only %d groups: group cap is now %d.", n_groups, cap
            )

    quota = allocate(population, n)
    used: Counter[str] = Counter()
    chosen: list[str] = []
    for t in sorted(quota):
        pools: dict[str, list[str]] = defaultdict(list)
        for name in ranked:
            if tercile[name] == t:
                pools[group_of.get(name, "")].append(name)
        for pool in pools.values():
            rng.shuffle(pool)
        need = quota[t]
        while need > 0:
            progressed = False
            for g in sorted(pools):
                if need > 0 and pools[g] and used[g] < cap:
                    chosen.append(pools[g].pop())
                    used[g] += 1
                    need -= 1
                    progressed = True
            if not progressed:
                break

    if len(chosen) < n:
        # The cap left a tercile short: fill from what is left, ignoring it.
        rest = sorted(set(ranked) - set(chosen))
        chosen += rng.sample(rest, n - len(chosen))
        logger.warning("The group cap left the subset short; filled.")
    sampled = dict(sorted(Counter(tercile[name] for name in chosen).items()))
    return Subset(sorted(chosen), population, sampled)


def load_samples(
    folder: Path,
    extract: Callable[[dict[str, Any], str], dict[str, Any] | None],
) -> list[dict[str, Any]]:
    """Read every `.json` file in a folder and turn each into a sample.

    Args:
        folder (Path): The dataset folder.
        extract (Callable[[dict[str, Any], str], dict[str, Any] | None]):
            Builds a sample from a file's parsed content and its file name,
            or returns None to skip the file.

    Returns:
        list[dict[str, Any]]: The samples, in file name order (the evaluation
            scripts use the file-system order, which would change the draws).
    """
    samples = []
    for json_file in sorted(folder.glob("*.json")):
        with open(json_file, "r") as file:
            data = json.load(file)
        sample = extract(data, json_file.name)
        if sample is not None:
            samples.append(sample)
    return samples


def _windows(data: dict[str, Any], filename: str) -> dict[str, Any]:
    return {
        "filename": filename,
        "input_window": data.get("input_window"),
        "output_window": data.get("output_window"),
    }


def _parse_name(filename: str) -> None:
    # The finance scripts read the ticker and the index from the file name, so
    # a malformed name stops the run while loading; keep that.
    filename.split("_")[1].split(".")[0]
    int(filename.split("_")[0])


def finance_trend_sample(
    data: dict[str, Any], filename: str
) -> dict[str, Any] | None:
    """Read a finance pair for the trend cells; None if the label is no str."""
    int(filename.split("_")[0])
    if isinstance(data.get("trend").get("output_bin_label"), str) is False:
        return None
    data.get("text").get("content")
    return {
        **_windows(data, filename),
        "bin_label": data.get("trend").get("output_bin_label"),
    }


def finance_forecast_sample(
    data: dict[str, Any], filename: str
) -> dict[str, Any]:
    """Read a finance pair for the forecast cells (windows only)."""
    data.get("text").get("content")
    data.get("technical").get("in_macd")
    return _windows(data, filename)


def finance_correlation_sample(
    data: dict[str, Any], filename: str
) -> dict[str, Any]:
    """Read a finance QA file for the correlation cells."""
    _parse_name(filename)
    return {
        "filename": filename,
        "correlation": data.get("news_price_correlation"),
    }


def finance_mcqa_sample(data: dict[str, Any], filename: str) -> dict[str, Any]:
    """Read a finance QA file for the MCQA cells."""
    _parse_name(filename)
    return {"filename": filename, "answer": data.get("MCQA").get("answer")}


def weather_sample(data: dict[str, Any], filename: str) -> dict[str, Any]:
    """Read a weather pair (windows only)."""
    return _windows(data, filename)


def weather_mcqa_sample(data: dict[str, Any], filename: str) -> dict[str, Any]:
    """Read a weather QA file for the MCQA cells."""
    return {"filename": filename, "answer": data.get("answer")}


@dataclass
class SubsetCell:
    """One cell's subset recipe.

    Attributes:
        name (str): The cell id (same as in the refactored run.py).
        draw (str): The draw id; cells with the same draw get the same items.
        folder (Callable[[argparse.Namespace], Path]): The full sample folder.
        extract (Callable[[dict[str, Any], str], Any]): The sample reader.
        label (Callable[[dict[str, Any]], str | None] | None): The label of a
            sample for label stratification; None for change stratification.
        grouped (bool): Whether to spread over stations (file name prefix).
    """

    name: str
    draw: str
    folder: Callable[[argparse.Namespace], Path]
    extract: Callable[[dict[str, Any], str], Any]
    label: Callable[[dict[str, Any]], str | None] | None = None
    grouped: bool = False


def _str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def build_cells() -> list[SubsetCell]:
    """Build the 22 cells, named as in the refactored run.py."""
    cells: list[SubsetCell] = []
    for setting in ("short", "long"):

        def pairs(a: argparse.Namespace, s: str = setting) -> Path:
            if a.finance_converted_dir is None:
                raise SystemExit("--finance-converted-dir is required.")
            return a.finance_converted_dir / s

        def qa(a: argparse.Namespace, s: str = setting) -> Path:
            return a.data_dir / "finance" / f"QA{s}"

        cells.append(
            SubsetCell(
                f"finance_trend_{setting}",
                f"finance_trend_{setting}",
                pairs,
                finance_trend_sample,
                lambda s: _str_or_none(s["bin_label"]),
            )
        )
        for indicator in ("time", "macd", "bb"):
            cells.append(
                SubsetCell(
                    f"finance_forecast_{indicator}_{setting}",
                    f"finance_forecast_{setting}",
                    pairs,
                    finance_forecast_sample,
                )
            )
        cells.append(
            SubsetCell(
                f"finance_correlation_{setting}",
                f"finance_correlation_{setting}",
                qa,
                finance_correlation_sample,
                lambda s: _str_or_none(s["correlation"]),
            )
        )
        cells.append(
            SubsetCell(
                f"finance_mcqa_{setting}",
                f"finance_mcqa_{setting}",
                qa,
                finance_mcqa_sample,
                lambda s: _str_or_none(s["answer"]),
            )
        )
    for setting, in_days, out_days in WEATHER_SETTINGS:

        def wpairs(
            a: argparse.Namespace, i: int = in_days, o: int = out_days
        ) -> Path:
            return a.data_dir / "weather" / f"aligned_in{i}days_out{o}days"

        def wqa(a: argparse.Namespace, s: str = setting) -> Path:
            return a.data_dir / "weather" / f"QA{s}"

        for past_future in ("past", "future"):

            def trend(s: dict[str, Any], pf: str = past_future) -> str:
                if pf == "past":
                    return compute_temperature_trend(s["input_window"])
                return compute_temperature_trend(
                    s["input_window"], s["output_window"]
                )

            name = f"weather_trend_{past_future}_{setting}"
            cells.append(SubsetCell(name, name, wpairs, weather_sample, trend))
        for task in ("forecast", "indicator"):
            name = f"weather_{task}_{setting}"
            cells.append(
                SubsetCell(name, name, wpairs, weather_sample, grouped=True)
            )
        name = f"weather_mcqa_{setting}"
        cells.append(
            SubsetCell(
                name,
                name,
                wqa,
                weather_mcqa_sample,
                lambda s: _str_or_none(s["answer"]),
            )
        )
    return cells


def draw_subset(
    cell: SubsetCell, args: argparse.Namespace
) -> tuple[Subset, int, int]:
    """Draw one cell's subset.

    Args:
        cell (SubsetCell): The cell.
        args (argparse.Namespace): The parsed arguments.

    Returns:
        tuple[Subset, int, int]: The subset, the number of usable items and
            the number left out because the label or change was unusable.
    """
    samples = load_samples(cell.folder(args), cell.extract)
    rng = make_rng(args.seed, cell.draw)
    if cell.label is not None:
        labels = {s["filename"]: cell.label(s) for s in samples}
        usable = {k: v for k, v in labels.items() if v is not None}
        subset = sample_by_label(usable, args.size, rng, args.min_per_label)
    else:
        changes = {s["filename"]: absolute_change(s) for s in samples}
        usable = {k: v for k, v in changes.items() if v is not None}
        groups = (
            {name: name.split("_")[0] for name in usable}
            if cell.grouped
            else None
        )
        subset = sample_by_change(
            usable, groups, args.size, rng, args.max_group_share
        )
    return subset, len(usable), len(samples) - len(usable)


def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--size", type=int, default=300, help="Items per cell")
    parser.add_argument(
        "--min-per-label",
        type=int,
        default=10,
        help="Minimum items per label where the set has that many",
    )
    parser.add_argument(
        "--max-group-share",
        type=float,
        default=0.05,
        help="Largest share of a cell for one station",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=ROOT / "data" / "processed",
        help="Folder with finance/QA* and weather/{aligned_*,QA*}",
    )
    parser.add_argument(
        "--finance-converted-dir",
        type=Path,
        default=None,
        help="Folder with short/ and long/ from convert_finance_parquet.py",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "subsets",
        help="Where to write <cell>.json and manifest.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the sizes and write nothing",
    )
    return parser.parse_args()


def main() -> None:
    """Draw every cell's subset and write the lists and the manifest."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    args = parse_args()
    manifest: dict[str, Any] = {}
    for cell in build_cells():
        subset, usable, unusable = draw_subset(cell, args)
        logger.info(
            "%s: %d usable (%d unusable), %d drawn; strata %s",
            cell.name,
            usable,
            unusable,
            len(subset.names),
            subset.sampled,
        )
        manifest[cell.name] = {
            "seed": args.seed,
            "draw": cell.draw,
            "usable": usable,
            "unusable": unusable,
            "population": subset.population,
            "sampled": subset.sampled,
        }
        if not args.dry_run:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            (args.output_dir / f"{cell.name}.json").write_text(
                json.dumps(subset.names, indent=1) + "\n"
            )
    if not args.dry_run:
        (args.output_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=1) + "\n"
        )


if __name__ == "__main__":
    main()
