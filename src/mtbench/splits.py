"""Group-safe train/test/audit splits on `meta.split_group`.

A group never appears in two splits (docs/harness_notes.md). Splitting by entity or by season is not
group-safe for sources where many entities share a group (nws_afd: stations of one office share texts
and weather), so use these helpers instead.
"""
import numpy as np

DEFAULT_FRACTIONS = {"train": 0.7, "test": 0.15, "audit": 0.15}


def assign_groups(groups, fractions: dict = None, seed: int = 0) -> dict:
    """group -> split name. Groups are shuffled with `seed` and cut by the fractions (by group count)."""
    fractions = fractions or DEFAULT_FRACTIONS
    unique = sorted(set(groups))
    order = np.random.default_rng(seed).permutation(len(unique))
    names, out, start = list(fractions), {}, 0
    cum = np.cumsum([fractions[n] for n in names]) / sum(fractions.values())
    for name, c in zip(names, cum):
        end = int(round(c * len(unique)))
        for i in order[start:end]:
            out[unique[i]] = name
        start = end
    return out


def split_samples(samples: list[dict], fractions: dict = None, seed: int = 0) -> dict:
    """{split name: [samples]} with whole split_groups assigned to one split."""
    assign = assign_groups([s["meta"]["split_group"] for s in samples], fractions, seed)
    out = {n: [] for n in (fractions or DEFAULT_FRACTIONS)}
    for s in samples:
        out[assign[s["meta"]["split_group"]]].append(s)
    return out


def shared_groups(splits: dict) -> set:
    """split_groups present in more than one split (empty for a group-safe split)."""
    seen: dict = {}
    for name, items in splits.items():
        for s in items:
            seen.setdefault(s["meta"]["split_group"], set()).add(name)
    return {g for g, names in seen.items() if len(names) > 1}


def by_key(samples: list[dict], key) -> dict:
    """Split by an arbitrary key (entity, season, ...) for checking it with shared_groups; not group-safe in general."""
    out: dict = {}
    for s in samples:
        out.setdefault(key(s), []).append(s)
    return out
