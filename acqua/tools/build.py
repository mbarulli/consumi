"""Assemble the final per-bill dataset for the water report.

Cost split (three real buckets + tax, matching how a Hera water bill is
actually structured):
  acqua      = volumetric acquedotto tariff (the water you drink)
  scarico    = fognatura + depurazione volumetric tariffs (sewerage + treatment)
  accessori  = fixed daily charges + UI/efficiency components + Fondo Fughe
               + net re-invoicing adjustments (conguagli, acconti)
  iva        = VAT

Reading-anchored consumption: the true meter delta per bill, taken from the
"Riepilogo letture" (read_mc). This sidesteps the negative/again-inflated
*billed* volumes produced by estimate-then-true-up cycles. The meter was
swapped ~Nov 2024 and the contract changed in Jan 2026, so reading values
restart; we key consumption off read_mc (already a delta, not an absolute),
which is immune to those restarts.
"""
import json

import os
from pathlib import Path

# Override with RAW2_JSON / FINAL_JSON when running outside the original sandbox.
RAW2 = Path(os.environ.get("RAW2_JSON", Path(__file__).resolve().parent / "raw2.json"))
FINAL = Path(os.environ.get("FINAL_JSON", "./final.json"))

blob = json.load(open(RAW2))
ids, data = blob["ids"], blob["data"]


def iso(d):
    dd, mm, yy = d.split(".")
    return f"{yy}-{mm}-{dd}"


def key6(fn):
    return fn[:6]


def cost_split(b):
    acqua = b.get("acquedotto|tariff", 0.0)
    scarico = b.get("fognatura|tariff", 0.0) + b.get("depurazione|tariff", 0.0)
    iva = 0.0  # added from scalar
    accessori = 0.0
    for k, v in b.items():
        if k in ("acquedotto|tariff", "fognatura|tariff", "depurazione|tariff"):
            continue
        accessori += v
    return round(acqua, 2), round(scarico, 2), round(accessori, 2)


import datetime as _dt

# Reading sanity. A bill's metered delta divided by the days it spans should look
# like household water use. Observed range across the whole history is 0.027–0.643
# m³/day (the low end being conguaglio bills whose reading window overlaps an
# earlier one), median 0.448. The 11/04→24/11/2024 bill was extracted as 2 m³ over
# 212 days = 0.009 m³/day — an order of magnitude below anything real — because a
# conguaglio arithmetic row was picked instead of the meter reading.
RATE_MIN, RATE_MAX = 0.02, 1.5


def _d(s):
    dd, mm, yy = s.split(".")
    return _dt.date(int(yy), int(mm), int(dd))


def vet_reading(r):
    """Return a list of human-readable warnings about this bill's meter reading."""
    warns = []
    cands = r.get("read_candidates") or []
    if len(cands) > 1:
        used = {"from": r.get("read_from"), "to": r.get("read_to"), "mc": r.get("read_mc")}
        warns.append(
            "letture ambigue: "
            + " | ".join(f"{c['from']:.0f}->{c['to']:.0f}={c['mc']:.0f}" for c in cands)
            + f" (usata {used['from']:.0f}->{used['to']:.0f}={used['mc']:.0f})"
        )
    mc, fd, td = r.get("read_mc"), r.get("read_from_date"), r.get("read_to_date")
    if mc is not None and fd and td:
        days = (_d(td) - _d(fd)).days
        if days > 0:
            rate = mc / days
            if not (RATE_MIN <= rate <= RATE_MAX):
                warns.append(f"consumo implausibile: {mc:.0f} m3 / {days} gg = {rate:.3f} m3/gg")
    return warns


records = []
for r in sorted(data, key=lambda x: iso(x["end"])):
    acqua, scarico, accessori = cost_split(r["buckets"])
    iva = r.get("iva", 0.0)
    rec = {
        "id": ids[key6(r["file"])],
        "start": iso(r["start"]),
        "end": iso(r["end"]),
        "mc_billed": r.get("billed_mc"),
        "mc_read": r.get("read_mc"),
        "acqua": acqua,
        "scarico": scarico,
        "accessori": round(accessori, 2),
        "iva": round(iva, 2),
        "tot": round(r["total"], 2),
    }
    # imponibile consistency: acqua+scarico+accessori should equal taxable
    imp = round(acqua + scarico + accessori, 2)
    rec["_imp_check"] = imp
    rec["_taxable"] = r.get("taxable")
    rec["_read_warns"] = vet_reading(r)
    if r.get("scanned"):
        rec["note"] = "bolletta cartacea (scansione, OCR)"
    records.append(rec)

# consistency report
print("period | mc_bill mc_read | acqua scarico access iva  tot | imp_ok")
prev_end = None
gaps = []
for r in records:
    ok = "ok" if r["_taxable"] is None or abs(r["_imp_check"] - r["_taxable"]) < 0.02 else f"!! {r['_imp_check']} vs {r['_taxable']}"
    if r["_read_warns"]:
        ok = "!! " + "; ".join(r["_read_warns"]) if ok == "ok" else ok + "; " + "; ".join(r["_read_warns"])
    print(f"{r['start']}->{r['end']} | {str(r['mc_billed']):>6} {str(r['mc_read']):>6} | "
          f"{r['acqua']:>6} {r['scarico']:>6} {r['accessori']:>6} {r['iva']:>5} {r['tot']:>7} | {ok}")

problems = []
for r in records:
    if r["_taxable"] is not None and abs(r["_imp_check"] - r["_taxable"]) >= 0.02:
        problems.append(f"{r['start']}->{r['end']}: imponibile {r['_imp_check']} vs {r['_taxable']}")
    for w in r["_read_warns"]:
        problems.append(f"{r['start']}->{r['end']}: {w}")

json.dump(records, open(FINAL, "w"), ensure_ascii=False, indent=1)
print("\nTotals:")
print("  bills:", len(records))
print("  sum mc_read:", round(sum(r["mc_read"] for r in records), 1))
print("  sum tot:", round(sum(r["tot"] for r in records), 2))
print("  sum acqua:", round(sum(r["acqua"] for r in records), 2))
print("  sum scarico:", round(sum(r["scarico"] for r in records), 2))
print("  sum accessori:", round(sum(r["accessori"] for r in records), 2))
print("  sum iva:", round(sum(r["iva"] for r in records), 2))

if problems:
    print(f"\n!! {len(problems)} PROBLEMA/I — non pubblicare, verificare a mano:")
    for p in problems:
        print("   " + p)
    raise SystemExit(1)
print("\nok: nessun problema di quadratura o di lettura")
