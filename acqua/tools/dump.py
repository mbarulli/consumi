"""Dump each Hera invoice page as column-ordered lines.

The bills are landscape A4 with a two-column layout; the "Dettaglio calcoli"
table can spill from the left column into the right one, so a naive
`pdftotext -layout` interleaves unrelated text into the table rows.
Here we cluster words by x-position into columns, then read each column
top-to-bottom, left column first.
"""
import sys, pdfplumber


def page_lines(page, ncols=2):
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    if not words:
        return []
    w = page.width
    bounds = [w * i / ncols for i in range(ncols + 1)]
    out = []
    for c in range(ncols):
        lo, hi = bounds[c], bounds[c + 1]
        col = [x for x in words if lo <= x["x0"] < hi]
        col.sort(key=lambda x: (round(x["top"] / 3), x["x0"]))
        cur, curtop = [], None
        for x in col:
            if curtop is None or abs(x["top"] - curtop) <= 3:
                cur.append(x)
                curtop = x["top"] if curtop is None else curtop
            else:
                out.append(" ".join(t["text"] for t in cur))
                cur, curtop = [x], x["top"]
        if cur:
            out.append(" ".join(t["text"] for t in cur))
    return out


def dump(path):
    lines = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            lines.append(f"### PAGE {i+1}")
            lines.extend(page_lines(page))
    return lines


if __name__ == "__main__":
    for ln in dump(sys.argv[1]):
        print(ln)
