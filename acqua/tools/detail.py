"""Classify every priced row of the 'Dettaglio calcoli' table.

Buckets are (service, kind):
  service ∈ acquedotto | fognatura | depurazione | fondo | altro
  kind    ∈ tariff     (volumetric water/sewerage/treatment tariff, incl. tiers)
            fixed      (quota fissa, €/day)
            component  (UI1..UI4, ex art. 36.3, quota recupero efficienza)
            fondo      (voluntary leak-insurance fund)
            adjust     (net-zero re-invoicing rows)
"""
import re

AMOUNT = re.compile(r"^-?\d{1,3}(?:\.\d{3})*,\d{2}$")


def num(s):
    return float(s.replace(".", "").replace(",", "."))


def norm(s):
    return re.sub(r"\s+", "", s).upper()


def line_amount(line):
    hits = [t for t in line.split() if AMOUNT.match(t)]
    return num(hits[-1]) if hits else None


SECTIONS = [
    ("QUOTAFISSAACQUEDOTTO", "fixed", "acquedotto"),
    ("QUOTAFISSAFOGNATURA", "fixed", "fognatura"),
    ("QUOTAFISSADEPURAZIONE", "fixed", "depurazione"),
    ("TARIFFAACQUEDOTTO", "tariff", "acquedotto"),
    ("TARIFFAFOGNATURA", "tariff", "fognatura"),
    ("TARIFFADEPURAZIONE", "tariff", "depurazione"),
    ("QUOTAFONDOFUGHE", "fondo", "fondo"),
]
COMPONENTS = ("COMPONENTEUI", "COMPONENTEEXART", "QUOTADARECUPEROEFFICIENZA")
# rows of the "Conguaglio anno solare" block: a bare section name + delta
CONGUAGLIO_ROW = re.compile(
    r"^(QUOTAFISSA|TARIFFAACQUEDOTTO|TARIFFAFOGNATURA|TARIFFADEPURAZIONE|"
    r"QUOTAFONDOFUGHE)(-?\d+,\d{2})\d*%?$")
CONGUAGLIO_TARGET = {
    "QUOTAFISSA": ("altro", "fixed"),
    "TARIFFAACQUEDOTTO": ("acquedotto", "tariff"),
    "TARIFFAFOGNATURA": ("fognatura", "tariff"),
    "TARIFFADEPURAZIONE": ("depurazione", "tariff"),
    "QUOTAFONDOFUGHE": ("fondo", "fondo"),
}

ACCONTO_MAP = [
    ("QUOTAFISSA", ("altro", "fixed")),
    ("TARIFFAACQUEDOTTO", ("acquedotto", "tariff")),
    ("TARIFFAFOGNATURA", ("fognatura", "tariff")),
    ("TARIFFADEPURAZIONE", ("depurazione", "tariff")),
    ("QUOTAFONDOFUGHE", ("fondo", "fondo")),
]


def parse(lines):
    buckets, totals, unclassified = {}, {}, []
    section = kind = service = None
    started = False

    def add(svc, k, amt):
        buckets[(svc, k)] = round(buckets.get((svc, k), 0.0) + amt, 2)

    for raw in lines:
        n = norm(raw)
        if n.startswith("DETTAGLIOCALCOLIDAL"):
            started = True
            continue
        if not started:
            continue
        if n.startswith(("SEZIONEIVA", "RIEPILOGOIVA", "INFORMAZIONICONTRATTO",
                         "ALTREINFORMAZIONI", "TOTALEFATTURA")):
            section = kind = service = None
            continue
        if "SUIMPONIBILE" in n or re.match(r"^\d+%-IVA", n):
            continue
        if n.startswith("TOTALE"):
            amt = line_amount(raw)
            if amt is not None:
                totals[re.sub(r"[\d,.%€]+$", "", n)] = amt
            continue
        m = CONGUAGLIO_ROW.match(n)
        if m:
            svc, k = CONGUAGLIO_TARGET[m.group(1)]
            add(svc, k, num(m.group(2)))
            section = kind = service = None
            continue

        if n.startswith("ACCONTIBOLLETTEPRECEDENTI"):
            amt = line_amount(raw)
            for key, target in ACCONTO_MAP:
                if key in n:
                    if amt is not None:
                        add(*target, amt)
                    break
            else:
                unclassified.append(raw)
            continue

        if n.startswith(("IMPORTOAL", "IMPORTOGIÀFATTURATO", "IMPORTOGIAFATTURATO")):
            amt = line_amount(raw)
            if amt is not None:
                add("altro", "adjust", amt)
            continue

        hit = next((s for s in SECTIONS if n.startswith(s[0])), None)
        if hit:
            section, kind, service = hit[0], hit[1], hit[2]
            continue
        if section is None:
            if line_amount(raw) is not None:
                unclassified.append(raw)
            continue

        if n.startswith(COMPONENTS):
            kind = "component"
            continue
        if n.startswith(("QUOTAFISSAFONDOFUGHE", "QUOTAVARIABILEFONDOFUGHE")):
            kind = "fondo"
        elif n.startswith("TARIFFA"):
            kind = "tariff"
        elif n.startswith("IMPORTODAL"):
            pass
        elif line_amount(raw) is not None:
            unclassified.append(raw)
            continue

        amt = line_amount(raw)
        if amt is not None:
            add(service, kind, amt)

    return buckets, totals, unclassified
