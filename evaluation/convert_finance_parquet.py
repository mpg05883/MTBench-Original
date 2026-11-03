"""Convert downloaded finance aligned pairs to JSON files for parity evaluation.

Example (run from the repository root):
    python evaluation/convert_finance_parquet.py \
        data/processed/finance/aligned_in7days_out1days \
        --output-dir data/processed/finance_converted/short

Requires pandas and a parquet engine such as pyarrow.
"""

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

SERIES_COLUMNS = [
    "input_timestamps", "input_window", "output_timestamps", "output_window"
]
JSON_COLUMNS = ["text", "trend", "technical", "alignment"]
logger = logging.getLogger(__name__)


def find_parquet_file(path: str | Path) -> Path:
    """Resolve a parquet file or the single table in a downloaded dataset."""
    path = Path(path)
    if path.is_file() and path.suffix == ".parquet":
        return path
    if not path.is_dir():
        raise FileNotFoundError(f"Parquet file or dataset folder not found: {path}")
    files = sorted(path.rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet file found in {path}")
    if len(files) != 1:
        raise ValueError(
            f"Expected one parquet file in {path}, found {len(files)}. "
            "Pass the intended file explicitly."
        )
    return files[0]


def save_to_json(data: dict, path: Path) -> None:
    """Write a pair, preserving NaN values as in the original JSON files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as file:
        json.dump(data, file, indent=4)


def convert_aligned_pairs(
    path: str | Path, output_dir: str | Path, max_rows: int | None = None
) -> int:
    """Write every row of the aligned-pairs parquet table as `<row>_pair.json`
    in `output_dir`.

    Each file has the keys of the original pair files, in the same order: the
    four series, then `text`, `trend`, `technical` and `alignment` decoded from
    their JSON strings. `NaN` values (the first Bollinger band value) are kept.

    Args:
        path (str | Path): The parquet file, or the downloaded dataset folder.
        output_dir (str | Path): Where to write the files. Created if missing.
        max_rows (int | None): Only convert the first N rows. None converts all
            of them.

    Returns:
        int: The number of files written.

    Raises:
        ValueError: If a column is missing or max_rows is negative.
    """
    if max_rows is not None and max_rows < 0:
        raise ValueError("max_rows must be nonnegative")
    # The table has no ticker column, so original <index>_<TICKER>.json names
    # cannot be rebuilt. Trend and forecast tasks only use the integer prefix.
    table = pd.read_parquet(find_parquet_file(path))
    missing = [
        c for c in SERIES_COLUMNS + JSON_COLUMNS if c not in table.columns
    ]
    if missing:
        raise ValueError(
            f"Missing column(s) in the parquet table: {', '.join(missing)}."
        )
    if max_rows is not None:
        table = table.iloc[:max_rows]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, row in enumerate(table.itertuples(index=False)):
        pair = {
            column: getattr(row, column).tolist() for column in SERIES_COLUMNS
        }
        pair.update(
            {
                column: json.loads(getattr(row, column))
                for column in JSON_COLUMNS
            }
        )
        save_to_json(pair, output_dir / f"{index}_pair.json")
    logger.info("Wrote %d files to %s", len(table), output_dir)
    return len(table)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Parquet file or dataset folder")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-rows", type=int, help="Convert only the first N rows")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    convert_aligned_pairs(args.path, args.output_dir, args.max_rows)


if __name__ == "__main__":
    main()
