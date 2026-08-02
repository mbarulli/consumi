"""Extract consumption + itemised costs from Hera water invoices.

Two text views of each PDF are used:
  * `pdftotext -layout` for scalar fields that live in prose-like blocks
    (readings, totals, billed volume);
  * a column-clustered view (dump.page_lines) for the "Dettaglio calcoli"
    table, which spills across the two-column landscape layout and is
    scrambled by -layout.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pdfplumber
from dump import page_lines
from detail import parse as parse_detail_lines

import os

# Directory holding the invoice PDFs, and where the raw extraction is written.
# Override with WATER_DIR / RAW_JSON when running outside the original sandbox.
WATER = Path(os.environ.get("WATER_DIR", "./water"))
RAW_OUT = Path(os.environ.get("RAW_JSON", "./raw.json"))

# ---------- helpers ----------------------------------------------------------

AMOUNT = re.compile(r"^-?\d{1,3}(?:\.\d{3})*,\d{2}$")


def num(s):
    return float(s.replace(".", "").replace(",", "."))


def norm(s):
    """Uppercase, strip every space — the column dump sometimes glues words."""
    return re.sub(r"\s+", "", s).upper()


def line_amount(line):
    """The single 2-decimal token on a detail row, if any."""
    hits = [t for t in line.split() if AMOUNT.match(t)]
    return num(hits[-1]) if len(hits) >= 1 else None


def layout_text(path):
    return subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        capture_output=True, text=True, check=True).stdout


def column_lines(path):
    out = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            out.extend(page_lines(page))
    return out


# ---------- scalar fields ----------------------------------------------------

RE_PERIOD = re.compile(r"Dettaglio calcoli dal (\d{2}\.\d{2}\.\d{4}) al (\d{2}\.\d{2}\.\d{4})")
RE_TOTALE = re.compile(r"Totale (?:fattura|contratto)\s+(-?[\d.]+,\d{2})\s*€")
RE_IVA = re.compile(r"IVA\s+(\d+)%\s+su imponibile\s+(-?[\d.]+,\d{2})\s*€\s+(-?[\d.]+,\d{2})")
RE_IVA2 = re.compile(r"Aliquota IVA (\d+)%\s+(-?[\d.]+,\d{2})\s+(-?[\d.]+,\d{2})")
RE_BILLED = re.compile(r"Consumo fatturato \(metri cubi\)\s+(-?[\d.]+,\d{3})")
RE_SUBCONS = re.compile(
    r"Consumo (rilevato|stimato) dal (\d{2}\.\d{2}\.\d{4}) al (\d{2}\.\d{2}\.\d{4})"
    r" \((\d+) giorni\)\s+(-?[\d.]+,\d{3}) mc")
RE_READ = re.compile(
    r"Consumo determinato dalla Lett(?:ura)?\.?\s+(.+?)\s+del\s+(\d{2}\.\d{2}\.\d{4})"
    r"\s+fino alla Lett(?:ura)?\.?\s+(.+?)\s+del\s+(\d{2}\.\d{2}\.\d{4})")
RE_MC3 = re.compile(r"-?[\d.]+,\d{3}")
RE_FATT = re.compile(r"fattura elettronica(?: valida ai fini fiscali)? (\d{10,})")


def parse_scalars(txt):
    flat = re.sub(r"[ \t]+", " ", txt)
    d = {}
    m = RE_PERIOD.search(flat)
    if m:
        d["start"], d["end"] = m.group(1), m.group(2)
    m = RE_TOTALE.search(flat)
    if m:
        d["total"] = num(m.group(1))
    m = RE_IVA.search(flat) or RE_IVA2.search(flat)
    if m:
        d["iva_rate"], d["taxable"], d["iva"] = int(m.group(1)), num(m.group(2)), num(m.group(3))
    m = RE_BILLED.search(flat)
    if m:
        d["billed_mc"] = num(m.group(1))
    m = RE_FATT.search(flat)
    if m:
        d["invoice_no"] = m.group(1)

    m = RE_READ.search(flat)
    if m:
        d["read_from_kind"], d["read_from_date"] = m.group(1).lower(), m.group(2)
        d["read_to_kind"], d["read_to_date"] = m.group(3).lower(), m.group(4)
        for ln in flat[m.end():m.end() + 2500].split("\n"):
            toks = RE_MC3.findall(ln)
            if len(toks) == 3:
                d["read_from"], d["read_to"], d["read_mc"] = map(num, toks)
                break
    d["components"] = [
        {"kind": k, "from": a, "to": b, "days": int(n), "mc": num(v)}
        for k, a, b, n, v in RE_SUBCONS.findall(flat)]
    return d


# ---------- main -------------------------------------------------------------

def process(path):
    rec = {"file": path.name}
    rec.update(parse_scalars(layout_text(path)))
    buckets, totals, unclassified = parse_detail_lines(column_lines(path))
    rec["buckets"] = {f"{s}|{k}": v for (s, k), v in buckets.items()}
    rec["section_totals"] = totals
    rec["unclassified"] = unclassified
    return rec


if __name__ == "__main__":
    out = [process(p) for p in sorted(WATER.glob("*.pdf"))]
    RAW_OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"{len(out)} invoices parsed")
