import numpy as np
import pytest

from mtbench import audit
from mtbench.adapters.base import SampleFilter
from mtbench.adapters import filters
from mtbench.splits import assign_groups, by_key, shared_groups, split_samples

from conftest import build_sample


def _samples(n_groups=10, per_group=6, stations_per_group=2):
    out = []
    for g in range(n_groups):
        for k in range(per_group):
            out.append(build_sample(
                entity=f"S{g}_{k % stations_per_group}", group=f"G{g}", text=f"text {g} {k}",
                start=f"2024-01-{1 + k:02d} 00:00:00", issue_time=f"2024-01-{1 + k:02d} 12:00:00",
                in_values=[float(10 + (i + k) % 24 + g) for i in range(48)],
                out_values=[float(12 + g + k)] * 24,
            ))
            out[-1]["meta"]["has_numeric_forecast"] = bool(k % 2)
    return out


def test_group_split_is_disjoint():
    parts = split_samples(_samples(), seed=1)
    assert shared_groups(parts) == set()
    assert sum(len(v) for v in parts.values()) == 60
    assert all(parts[n] for n in parts)


def test_assign_groups_is_seeded_and_covers_all():
    a, b = assign_groups(["a", "b", "c", "d"], seed=3), assign_groups(["a", "b", "c", "d"], seed=3)
    assert a == b and set(a) == {"a", "b", "c", "d"}


def test_entity_and_season_splits_share_groups():
    samples = _samples()
    by_station = by_key(samples, lambda s: s["meta"]["entity_id"])
    split_a = {"train": [x for k, v in by_station.items() if k.endswith("_0") for x in v],
               "test": [x for k, v in by_station.items() if k.endswith("_1") for x in v]}
    assert len(shared_groups(split_a)) == 10  # every group has a station on each side
    by_day = by_key(samples, lambda s: s["meta"]["issue_time"][:10] > "2024-01-03")
    assert shared_groups({"a": by_day[True], "b": by_day[False]})


def test_per_entity_dedup_keeps_the_same_text_at_two_entities():
    texts = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron"
    flt = SampleFilter(dedup_by=lambda s: s["meta"]["entity_id"])
    a, b = build_sample(entity="A", text=texts), build_sample(entity="B", text=texts)
    assert flt.apply(a) and flt.apply(b)
    assert not flt.apply(build_sample(entity="A", text=texts))  # same station again -> duplicate


def test_global_dedup_default_still_drops_across_entities():
    flt = SampleFilter()
    texts = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron"
    assert flt.apply(build_sample(entity="A", text=texts))
    assert not flt.apply(build_sample(entity="B", text=texts))


def test_noaa_folder_files_are_windows_for_their_station(tmp_path):
    import json
    d = tmp_path / "noaa_aligned_in7days_out1days"
    d.mkdir()
    s = build_sample(entity="USW1")
    (d / "USW1_2024-01-07_ctrl.json").write_text(json.dumps(s))
    assert filters.load_mtbench_windows([tmp_path]) == {}  # default skips noaa_
    w = filters.load_mtbench_windows([tmp_path], skip_prefixes=())
    assert list(w) == ["USW1"]
    assert filters.check_overlap(build_sample(entity="USW1"), w) == "overlaps_mtbench"


def test_naive_comparison_keys():
    out = audit.naive_comparison(_samples())
    assert set(out) == {"all", "numeric", "rest"}
    assert out["all"]["n"] == 60 and out["numeric"]["n"] + out["rest"]["n"] == 60
    for k in ("persistence_last", "persistence_last_period_mean", "const_median_shift", "ts_only", "text_only",
              "text_over_best_naive", "text_over_ts_only"):
        assert np.isfinite(out["all"][k])
