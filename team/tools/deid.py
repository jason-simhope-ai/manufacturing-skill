#!/usr/bin/env python3
"""De-identify a CSV export at the source (spec 11.1 / 13.3).

    deid.py --in FILE.csv --out FILE.csv --map team/local/deid-map.local.yaml
            [--drop COL,...] [--keep COL,...] [--text COL,...]
            [--customer-cols COL,...] [--denylist FILE]

* customer names -> stable CUST-xx ids (mapping table lives in the local map)
* --drop removes columns; --keep keeps only the listed columns
* free-text cells are scanned with the DLP patterns (spec 11.1) plus the local
  denylist (regex per line, default: names.denylist next to the map). Known
  customer names inside free text are replaced; any remaining hit is residual
  and nothing is written (exit 1). Matched values are never printed.

The map holds real customer names, so it must be a `*.local.*` file or live
outside the repository.

Exit codes: 0 OK, 1 residual hits, 2 usage or IO error.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _teamlib as lib  # noqa: E402

CUSTOMER_COL = re.compile(r"customer|client|客戶", re.I)


def _csv_list(s):
    return [c.strip() for c in s.split(",") if c.strip()] if s else []


def _load_denylist(path: Path):
    pats = []
    if path.is_file():
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
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
              denylist):
    """Pure core: returns (out_header, out_rows, counts, residual list)."""
    counts = {"customer": 0, "customer_in_text": 0, "dropped_columns": 0,
              "residual": 0}
    idx = list(range(len(header)))
    if keep:
        idx = [i for i in idx if header[i] in keep]
    kept = [i for i in idx if header[i] not in drop]
    counts["dropped_columns"] = len(header) - len(kept)
    folded = {k.casefold(): v for k, v in mapping.items()}
    # Pre-pass: assign ids to every customer name first, so a name that shows
    # up in free text before its own column cell is still replaced.
    for row in rows:
        for i in kept:
            if header[i] in customer_cols and i < len(row) and row[i].strip():
                v = row[i].strip()
                if v.casefold() not in folded:
                    mapping[v] = folded[v.casefold()] = _next_id(mapping)
    names = sorted(mapping, key=len, reverse=True)
    out, residual = [], []
    for r, row in enumerate(rows, start=2):
        new = []
        for i in kept:
            col = header[i]
            cell = row[i] if i < len(row) else ""
            if col in customer_cols:
                v = cell.strip()
                if v:
                    counts["customer"] += 1
                    cell = folded[v.casefold()]
                new.append(cell)
                continue
            for nm in names:
                rx = re.compile(re.escape(nm), re.I)
                cell, k = rx.subn(mapping[nm], cell)
                counts["customer_in_text"] += k
            if not text_cols or col in text_cols:
                classes = lib.dlp_scan(cell)
                if any(p.search(cell) for p in denylist):
                    classes.append("denylist")
                for c in classes:
                    residual.append((r, col, c))
            new.append(cell)
        out.append(new)
    counts["residual"] = len(residual)
    return [header[i] for i in kept], out, counts, residual


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
        before = dict(mapping)
        out_h, out_rows, counts, residual = deid_rows(
            rows, header, mapping=mapping, customer_cols=set(cols),
            drop=set(_csv_list(args.drop)), keep=set(_csv_list(args.keep)),
            text_cols=set(_csv_list(args.text)), denylist=denylist)
    except (OSError, ValueError, lib.LoadError, UnicodeDecodeError) as e:
        print(f"deid: {e}", file=sys.stderr)
        return 2
    print(f"deid: rows={len(rows)} customers replaced={counts['customer']} "
          f"in-text={counts['customer_in_text']} "
          f"columns dropped={counts['dropped_columns']} "
          f"residual hits={counts['residual']}")
    if residual:
        for r, col, cls in residual[:20]:
            print(f"residual: row {r} column {col!r} matches {cls}")
        print("deid: residual hits remain; nothing written. Clean the source "
              "or extend the map / drop the column.")
        return 1
    try:
        if mapping != before:
            map_path.parent.mkdir(parents=True, exist_ok=True)
            mdata["schema"] = 1
            mdata["customers"] = mapping
            map_path.write_text(lib.yaml.safe_dump(
                mdata, allow_unicode=True, sort_keys=True), encoding="utf-8")
        with out_path.open("w", newline="", encoding="utf-8") as fp:
            w = csv.writer(fp, lineterminator="\n")
            w.writerow(out_h)
            w.writerows(out_rows)
    except OSError as e:
        print(f"deid: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
