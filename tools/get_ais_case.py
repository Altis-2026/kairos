import argparse
import csv
import io
import json
import os
import sys
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone

BASE = "https://coast.noaa.gov/htdata/CMSP/AISDataHandler"

USAGE = """
Downloads one day of public AIS vessel-transponder data from MarineCadastre
(NOAA and BOEM) and installs the slice Kairos needs for its dark-vessel case.

Default case: the Mississippi River delta in the Gulf of Mexico, 2023-01-15.
From the repo root:

    python tools/get_ais_case.py

The daily national file is large (roughly 100-200 MB zipped), so this streams
it, keeps only the records inside the case bounding box, and writes a small
JSON into backend/data/ais/. Nothing else is stored.

Other options:
    --case gulf-delta-2023      which case in gee/dark_vessels.py to fill
    --date 2023-01-15           override the day to download
    --keep-hours 6              hours either side of noon UTC to keep
"""

CASES = {
    "gulf-delta-2023": {
        "bbox": [-89.6, 28.6, -88.9, 29.2],
        "date": "2023-01-15",
    },
}


def parse_args():
    p = argparse.ArgumentParser(
        description="Fetch public AIS data for a Kairos dark-vessel case.",
        epilog=USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--case", default="gulf-delta-2023")
    p.add_argument("--date", default=None)
    p.add_argument("--keep-hours", type=float, default=6.0)
    return p.parse_args()


def to_epoch_ms(stamp: str) -> int:
    # MarineCadastre uses "2023-01-15T00:00:02" in UTC.
    dt = datetime.strptime(stamp[:19], "%Y-%m-%dT%H:%M:%S").replace(
        tzinfo=timezone.utc
    )
    return int(dt.timestamp() * 1000)


def main():
    args = parse_args()
    case = CASES.get(args.case)
    if case is None:
        print(f"Unknown case '{args.case}'. Known: {list(CASES)}")
        return 1

    date = args.date or case["date"]
    year = date[:4]
    name = f"AIS_{date.replace('-', '_')}"
    url = f"{BASE}/{year}/{name}.zip"

    min_lon, min_lat, max_lon, max_lat = case["bbox"]
    midday = datetime.strptime(date, "%Y-%m-%d").replace(
        hour=12, tzinfo=timezone.utc
    )
    keep_from = midday - timedelta(hours=args.keep_hours)
    keep_to = midday + timedelta(hours=args.keep_hours)

    print(f"Downloading {url}")
    print("This file is large; the download is the slow part.")
    try:
        with urllib.request.urlopen(url) as resp:
            blob = resp.read()
    except Exception as e:
        print(f"Download failed: {e}")
        print("Check the date exists in the MarineCadastre archive.")
        return 1

    print(f"Got {len(blob) / 1e6:.0f} MB, filtering to the case area")
    records = []
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        inner = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not inner:
            print("No CSV inside the archive.")
            return 1
        with zf.open(inner[0]) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"))
            for row in reader:
                try:
                    lon = float(row["LON"])
                    lat = float(row["LAT"])
                except (KeyError, TypeError, ValueError):
                    continue
                if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
                    continue
                try:
                    t = to_epoch_ms(row["BaseDateTime"])
                except (KeyError, ValueError):
                    continue
                if not (
                    keep_from.timestamp() * 1000 <= t <= keep_to.timestamp() * 1000
                ):
                    continue
                length = row.get("Length") or ""
                records.append(
                    {
                        "mmsi": row.get("MMSI"),
                        "name": (row.get("VesselName") or "").strip() or None,
                        "length_m": float(length) if length else None,
                        "lon": round(lon, 5),
                        "lat": round(lat, 5),
                        "t": t,
                    }
                )

    if not records:
        print("No AIS records fell inside the case box and time window.")
        return 1

    out_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "backend",
        "data",
        "ais",
    )
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{args.case}.json")
    payload = {
        "case": args.case,
        "source": "MarineCadastre.gov (NOAA and BOEM) daily AIS archive",
        "source_file": f"{name}.zip",
        "bbox": case["bbox"],
        "window": {
            "from": keep_from.strftime("%Y-%m-%d %H:%M UTC"),
            "to": keep_to.strftime("%Y-%m-%d %H:%M UTC"),
        },
        "records": records,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f)

    vessels = len({r["mmsi"] for r in records})
    print(f"Wrote {len(records)} positions from {vessels} vessels")
    print(f"  {out_path}")
    print("Restart the backend and open the Dark Vessels panel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
