#!/usr/bin/env python3
r"""De-identify a CSV export at the source (spec 11.1 / 13.3). Fails closed.

    deid.py --in FILE.csv --out FILE.csv --map team/local/deid-map.local.yaml
            [--drop COL,...] [--keep COL,...] [--text COL,...]
            [--customer-cols COL,...] [--denylist FILE] [--partno-pattern REGEX]
            [--allow-residual]

* every cell is NFKC-normalised, stripped of invisible/format characters, and
  matched with whitespace folded, so `Acme  Precision` and full-width `ＡＣＭＥ`
  are the same customer
* customer names -> stable CUST-xx ids (mapping table lives in the local map);
  inside free text names are matched as whole tokens (`AB` never rewrites `ABOUT`)
* --drop removes columns; --keep keeps only the listed columns
* residual scan (all kept non-customer columns, or only --text ones): DLP markers,
  UBN / national id / NT$ amounts, emails, Taiwan mobile and landline numbers,
  surname + title names (a common surname, up to 3 more CJK chars, then a
  title or honorific), the local denylist; and any
  non-placeholder value left in a contact column (聯絡人 / contact / ship_to /
  attention / attn), which must be dropped or mapped
* the denylist is `--denylist FILE`, else `names.denylist` next to --map. The run always says
  whether one was loaded and how many entries it has, and warns loudly when there is none
* part / drawing numbers are scanned ONLY with `--partno-pattern REGEX` (your own shape, e.g.
  `DWG-[A-Z]{2}\d{5}|PN-\d{5}-[A-Z]`); without it they pass through, and the run says so
* not scanned in any case: English names or aliases that are not in the map or the denylist,
  LINE ids and other handles. Spot-check at least 10 output rows by eye before sharing
* rows with more or fewer cells than the header (unquoted commas) are reported; extra cells are dropped
* any residual hit -> report per row and per column, nothing written, exit 1,
  unless --allow-residual (written anyway, still reported). Values are never printed.

The map holds real customer names, so it must be a `*.local.*` file or live
outside the repository. Output and map are written 0600.

Exit codes: 0 OK, 1 residual hits, 2 usage or IO error.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _teamlib as lib  # noqa: E402

CUSTOMER_COL = re.compile(r"customer|client|buyer|客戶|買方", re.I)
CONTACT_COL = re.compile(r"聯絡人|聯絡|contact|ship[\s_-]*to|attention|attn|收件人", re.I)
PLACEHOLDER_ONLY = re.compile(r"^(?:CUST-\d+[\s,;/、]*)*$")
_INVISIBLE_EXTRA = re.compile(
    "[\u034f\u115f\u1160\u180b-\u180d\u3164\ufe00-\ufe0f\uffa0\U000e0100-\U000e01ef]")
_WS = re.compile(r"\s+")


def clean(text: str) -> str:
    """NFKC + drop format/zero-width/variation-selector characters (keeps spacing)."""
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return unicodedata.normalize("NFKC", _INVISIBLE_EXTRA.sub("", text))


def fold(text: str) -> str:
    """Matching key: clean + collapse whitespace + casefold."""
    return _WS.sub(" ", clean(text)).strip().casefold()


def name_pattern(name: str) -> re.Pattern:
    """Whole-token, whitespace-tolerant, case-insensitive matcher for a customer name."""
    tokens = fold(name).split(" ")
    body = r"\s+".join(re.escape(t) for t in tokens)
    if re.match(r"[0-9a-z]", tokens[0]):
        body = r"(?<![0-9A-Za-z])" + body
    if re.search(r"[0-9a-z]$", tokens[-1]):
        body += r"(?![0-9A-Za-z])"
    return re.compile(body, re.I)


def residual_classes(cell: str, denylist, partno=None) -> list[str]:
    squeezed = _WS.sub("", cell)
    classes = lib.dlp_scan(cell)
    classes += [n for n, rx in lib.PII_PATTERNS if rx.search(cell)]
    if partno is not None and (partno.search(cell) or partno.search(squeezed)):
        classes.append("part-number")
    if any(p.search(cell) or p.search(squeezed) for p in denylist):
        classes.append("denylist")
    return classes


def _csv_list(s):
    return [c.strip() for c in s.split(",") if c.strip()] if s else []


def _load_denylist(path: Path):
    pats = []
    if path.is_file():
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.startswith("T3:"):      # gateway tier marker; any hit is a residual here
                s = s[3:].strip()
            try:
                pats.append(re.compile(s))
            except re.error as e:
                raise ValueError(f"{path}:{n}: bad regex ({e})")
    return pats


def _next_id(mapping: dict) -> str:
    nums = [int(m.group(1)) for v in mapping.values()
            if (m := re.fullmatch(r"CUST-(\d+)", str(v)))]
    n = (max(nums) if nums else 0) + 1
    return f"CUST-{n:02d}"


def _map_is_safe(map_path: Path) -> bool:
    if ".local." in map_path.name:
        return True
    try:
        map_path.resolve().relative_to(lib.TOOL_REPO)
    except ValueError:
        return True  # outside the repository
    return False


def deid_rows(rows, header, *, mapping, customer_cols, drop, keep, text_cols,
              denylist, contact_cols=None, partno=None):
    """Pure core: returns (out_header, out_rows, counts, residual list)."""
    counts = {"customer": 0, "customer_in_text": 0, "dropped_columns": 0,
              "residual": 0, "ragged_rows": 0, "ragged_first": None}
    idx = list(range(len(header)))
    if keep:
        idx = [i for i in idx if header[i] in keep]
    kept = [i for i in idx if header[i] not in drop]
    counts["dropped_columns"] = len(header) - len(kept)
    if contact_cols is None:
        contact_cols = {h for h in header if CONTACT_COL.search(clean(h))}
    folded = {fold(k): v for k, v in mapping.items()}
    # Pre-pass: assign ids to every customer name first, so a name that shows
    # up in free text before its own column cell is still replaced.
    for row in rows:
        for i in kept:
            if header[i] in customer_cols and i < len(row) and fold(row[i]):
                key = fold(row[i])
                if key not in folded:
                    shown = _WS.sub(" ", clean(row[i])).strip()
                    mapping[shown] = folded[key] = _next_id(mapping)
    pats = [(name_pattern(k), v) for k, v in sorted(
        folded.items(), key=lambda kv: len(kv[0]), reverse=True) if k]
    out, residual = [], []
    for r, row in enumerate(rows, start=2):
        if len(row) != len(header):
            counts["ragged_rows"] += 1
            if counts["ragged_first"] is None:
                counts["ragged_first"] = (r, len(row))
        new = []
        for i in kept:
            col = header[i]
            cell = clean(row[i] if i < len(row) else "")
            if col in customer_cols:
                if fold(cell):
                    counts["customer"] += 1
                    cell = folded[fold(cell)]
                new.append(cell)
                continue
            for rx, cid in pats:
                cell, k = rx.subn(cid, cell)
                counts["customer_in_text"] += k
            classes = []
            if not text_cols or col in text_cols or col in contact_cols:
                classes = residual_classes(cell, denylist, partno)
            if col in contact_cols and not PLACEHOLDER_ONLY.match(cell.strip()):
                classes.append("contact-column")
            for c in dict.fromkeys(classes):
                residual.append((r, col, c))
            new.append(cell)
        out.append(new)
    counts["residual"] = len(residual)
    return [header[i] for i in kept], out, counts, residual


def scan_report(deny_path: Path, denylist, partno: str | None) -> list[str]:
    """What this run did and did not look for, so `residual hits=0` is never read as 'clean'."""
    lines = []
    if denylist:
        lines.append(f"deid: scanned = generic patterns (DLP words, UBN, amounts, email, phone, surname+title) "
                     f"+ denylist {len(denylist)} entries from {deny_path}")
    else:
        lines.append("deid: scanned = generic patterns (DLP words, UBN, amounts, email, phone, surname+title) only")
        lines.append(f"deid: WARNING no denylist loaded (none at {deny_path}, or it has no entries): "
                     "customer aliases, drawing numbers and project codes are NOT checked. "
                     "Fill team/local/names.denylist or pass --denylist FILE")
    pn = f"regex '{partno}'" if partno else "NOT scanned (no --partno-pattern)"
    lines.append(f"deid: part-number scan = {pn}")
    lines.append("deid: NOT scanned: English names or aliases that are not in the map or denylist, LINE ids and "
                 "other handles. Spot-check at least 10 output rows by eye before sharing")
    return lines


def _write_private(path: Path, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.chmod(path, 0o600)
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as fp:
        fp.write(text)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="deid.py", description=__doc__.split(
        "\n")[0])
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--drop", default="")
    ap.add_argument("--keep", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--customer-cols", default="")
    ap.add_argument("--denylist")
    ap.add_argument("--partno-pattern", dest="partno", metavar="REGEX",
                    help="also treat matches of this regex (your part/drawing number shape) as residual")
    ap.add_argument("--allow-residual", action="store_true",
                    help="write the output even with residual hits (still reported)")
    args = ap.parse_args(argv)
    map_path, in_path, out_path = Path(args.map), Path(args.inp), Path(args.out)
    if not _map_is_safe(map_path):
        print("deid: --map holds real customer names; name it *.local.* "
              "(gitignored) or keep it outside the repository",
              file=sys.stderr)
        return 2
    try:
        with in_path.open(newline="", encoding="utf-8-sig") as fp:
            data = list(csv.reader(fp))
        if not data:
            print("deid: input CSV is empty", file=sys.stderr)
            return 2
        header, rows = data[0], data[1:]
        mdata = {}
        if map_path.is_file():
            mdata = lib.load_roster(map_path)
        mapping = dict(mdata.get("customers") or {})
        if not all(isinstance(k, str) and isinstance(v, str)
                   for k, v in mapping.items()):
            print("deid: map.customers must map strings to strings",
                  file=sys.stderr)
            return 2
        cols = _csv_list(args.customer_cols) or list(
            mdata.get("customerColumns") or []) or [
            h for h in header if CUSTOMER_COL.search(h)]
        deny_path = Path(args.denylist) if args.denylist else (
            map_path.parent / "names.denylist")
        denylist = _load_denylist(deny_path)
        try:
            partno = re.compile(args.partno) if args.partno else None
        except re.error as e:
            print(f"deid: bad --partno-pattern ({e})", file=sys.stderr)
            return 2
        before = dict(mapping)
        out_h, out_rows, counts, residual = deid_rows(
            rows, header, mapping=mapping, customer_cols=set(cols),
            drop=set(_csv_list(args.drop)), keep=set(_csv_list(args.keep)),
            text_cols=set(_csv_list(args.text)), denylist=denylist,
            partno=partno)
    except (OSError, ValueError, lib.LoadError, UnicodeDecodeError) as e:
        print(f"deid: {e}", file=sys.stderr)
        return 2
    print(f"deid: rows={len(rows)} customers replaced={counts['customer']} "
          f"in-text={counts['customer_in_text']} "
          f"columns dropped={counts['dropped_columns']} "
          f"residual hits={counts['residual']}")
    for line in scan_report(deny_path, denylist, args.partno):
        print(line)
    if counts["ragged_rows"]:
        r, n = counts["ragged_first"]
        print(f"deid: WARNING {counts['ragged_rows']} row(s) do not have {len(header)} cells "
              f"(first: row {r} has {n}); extra cells are dropped, missing ones read as empty. "
              "Quote commas in the source export.")
    if residual:
        for r, col, cls in residual[:20]:
            print(f"residual: row {r} column {col!r} matches {cls}")
        per_col: dict[str, dict[str, int]] = {}
        for _r, col, cls in residual:
            per_col.setdefault(col, {}).setdefault(cls, 0)
            per_col[col][cls] += 1
        for col, classes in per_col.items():
            detail = ", ".join(f"{c}={n}" for c, n in classes.items())
            print(f"residual column {col!r}: {sum(classes.values())} ({detail})")
        if not args.allow_residual:
            print("deid: residual hits remain; nothing written. Clean the source, "
                  "extend the map / denylist, or drop the column (--allow-residual "
                  "writes anyway).")
            return 1
        print("deid: WARNING --allow-residual: output written WITH residual hits; "
              "review it before sharing.")
    try:
        if mapping != before:
            map_path.parent.mkdir(parents=True, exist_ok=True)
            mdata["schema"] = 1
            mdata["customers"] = mapping
            _write_private(map_path, lib.yaml.safe_dump(
                mdata, allow_unicode=True, sort_keys=True))
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(out_h)
        w.writerows(out_rows)
        _write_private(out_path, buf.getvalue())
    except OSError as e:
        print(f"deid: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
