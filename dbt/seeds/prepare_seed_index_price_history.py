"""One-time/rerun-on-refresh transform: investing.com-style index history export
(quoted, comma-grouped numbers, M/B/K-suffixed volume, MM/DD/YYYY dates) into the
committed dbt seed CSV. Not part of the dbt build itself - run manually whenever a
new export needs to replace or extend seed_index_price_history.csv, then re-run
`dbt seed`. See docs/warehouse/DECISIONS.md ("Index price history seed") for why
this exists outside the extract/ pipeline.

Usage: python prepare_seed_index_price_history.py <source.csv> <index_name>
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

VOLUME_SUFFIXES = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}


def parse_number(raw: str) -> str:
    return raw.replace(",", "")


def parse_volume(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    suffix = raw[-1].upper()
    if suffix in VOLUME_SUFFIXES:
        return str(int(float(raw[:-1]) * VOLUME_SUFFIXES[suffix]))
    return parse_number(raw)


def parse_pct(raw: str) -> str:
    return raw.replace("%", "")


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    source_path = Path(sys.argv[1])
    index_name = sys.argv[2]
    out_path = Path(__file__).parent / "seed_index_price_history.csv"

    rows = []
    with source_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_iso = datetime.strptime(row["Date"], "%m/%d/%Y").date().isoformat()
            rows.append(
                {
                    "index_name": index_name,
                    "date": date_iso,
                    "open": parse_number(row["Open"]),
                    "high": parse_number(row["High"]),
                    "low": parse_number(row["Low"]),
                    "close": parse_number(row["Price"]),
                    "volume": parse_volume(row["Vol."]),
                    "change_pct": parse_pct(row["Change %"]),
                }
            )

    rows.sort(key=lambda r: (r["index_name"], r["date"]))

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "index_name",
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "change_pct",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
