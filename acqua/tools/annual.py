"""Extend the reading-anchored annual consumption (`annualReal`) with new bills.

Why incremental and not a full recompute
----------------------------------------
`annualReal` is NOT the sum of per-bill consumption: conguaglio bills re-cover
periods already billed in acconto, so summing bills double-counts. It is
reconstructed from the chain of *physical* meter readings, pro-rated per day
across calendar years.

That historical chain crosses two discontinuities (meter swap ~Nov 2024, and a
cessazione+attivazione in Jan 2026) whose handling was decided case-by-case when
the report was first built. A blind full recompute does not reproduce the
published figures across those resets, so this script does not attempt one.
Instead it treats the published `annualReal` as a trusted baseline and only
extends it with reading intervals that appear *after* the last anchor already
accounted for.

Closed years therefore never move; only the years touched by genuinely new
readings change.

State lives in annual_state.json:
  {"annualReal": {...}, "last_anchor": {"date": "YYYY-MM-DD", "value": <m3>}}

Usage:
  python3 annual.py                 # report what would change
  python3 annual.py --write         # persist updated annual_state.json

Exits non-zero (and changes nothing) if the chain shows a meter reset — that
needs a human decision, exactly as the Nov-2024 swap did.
"""
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw2.json"
STATE = HERE / "annual_state.json"

# Readings labelled "stimata" are Hera's estimates, later trued up by conguaglio.
# Only physical reads anchor the chain.
ESTIMATED = "stimata"


def iso(s):
    dd, mm, yy = s.split(".")
    return dt.date(int(yy), int(mm), int(dd))


def real_anchors(data):
    """Every physical (non-estimated) reading, de-duplicated, date-ordered."""
    seen = {}
    for bill in data:
        for side in ("from", "to"):
            value = bill.get(f"read_{side}")
            date_s = bill.get(f"read_{side}_date")
            kind = bill.get(f"read_{side}_kind") or ""
            if value is None or not date_s or ESTIMATED in kind:
                continue
            seen.setdefault(iso(date_s), set()).add(value)
    out = []
    for date in sorted(seen):
        for value in sorted(seen[date]):
            out.append((date, value))
    return out


def prorate(d1, v1, d2, v2):
    """Split the consumption between two anchors pro-die across calendar years."""
    delta = v2 - v1
    days = (d2 - d1).days
    per = defaultdict(float)
    if days <= 0 or delta <= 0:
        return per
    cur = d1
    while cur < d2:
        year_end = dt.date(cur.year, 12, 31) + dt.timedelta(days=1)
        seg_end = min(d2, year_end)
        per[str(cur.year)] += delta * (seg_end - cur).days / days
        cur = seg_end
    return per


def main():
    state = json.loads(STATE.read_text())
    annual = dict(state["annualReal"])
    last_date = dt.date.fromisoformat(state["last_anchor"]["date"])
    last_value = state["last_anchor"]["value"]

    anchors = real_anchors(json.loads(RAW.read_text())["data"])
    new = [(d, v) for d, v in anchors if d > last_date]

    if not new:
        print("no new physical readings — annualReal unchanged")
        return 0

    chain = [(last_date, last_value)] + new
    for (d1, v1), (d2, v2) in zip(chain, chain[1:]):
        if v2 < v1:
            print(
                f"STOP: meter reset detected ({v1} on {d1} -> {v2} on {d2}).\n"
                "A swap/contract change needs the same manual segmenting the "
                "Nov-2024 swap got. Do not publish; surface this to Marco.",
                file=sys.stderr,
            )
            return 1

    added = defaultdict(float)
    for (d1, v1), (d2, v2) in zip(chain, chain[1:]):
        for year, mc in prorate(d1, v1, d2, v2).items():
            added[year] += mc

    for year, mc in sorted(added.items()):
        before = annual.get(year, 0.0)
        annual[year] = round(before + mc, 1)
        print(f"  {year}: {before:>6.1f} -> {annual[year]:>6.1f}  (+{mc:.1f} m3)")

    state["annualReal"] = {k: annual[k] for k in sorted(annual)}
    state["last_anchor"] = {"date": chain[-1][0].isoformat(), "value": chain[-1][1]}

    if "--write" in sys.argv:
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n")
        print(f"\nwrote {STATE}")
        print("Now mirror this into the report's `const annualReal = {...};` line:")
    else:
        print("\n(dry run — pass --write to persist)")
    print(json.dumps(state["annualReal"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
