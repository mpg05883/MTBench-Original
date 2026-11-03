"""Read the filename lists produced by make_parity_subsets.py."""

import json
from pathlib import Path


def dataset_files(folder: Path, subset_file: str | None = None) -> list[Path]:
    """Return the selected files in list order, failing on missing samples.

    Without a subset list, preserve the evaluators' full-dataset behavior.
    """
    if subset_file is None:
        return list(folder.glob("*.json"))

    names = json.loads(Path(subset_file).read_text())
    if not isinstance(names, list) or any(
        not isinstance(name, str)
        or Path(name).name != name
        or "/" in name
        or "\\" in name
        or not name.endswith(".json")
        for name in names
    ):
        raise ValueError(f"Expected a JSON list of sample filenames: {subset_file}")
    if len(names) != len(set(names)):
        raise ValueError(f"Duplicate sample filenames in {subset_file}")

    files = [folder / name for name in names]
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(f"Subset sample does not exist: {path}")
    return files
