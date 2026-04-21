"""
Download SLV options daily bars from Massive.com flat files (S3).

Each daily flat file contains ALL US options. We download, filter for SLV,
and save. ~3MB compressed per day, ~730 files for 2 years.
"""

import csv
import gzip
import io
import json
import os
from datetime import date, timedelta
from pathlib import Path

import boto3

# S3 credentials
S3_ENDPOINT = "https://files.massive.com"
S3_ACCESS_KEY = os.environ.get("MASSIVE_S3_ACCESS_KEY", "611ae18d-910d-4dc2-b6c3-ac35ace944cc")
S3_SECRET_KEY = os.environ.get("MASSIVE_S3_SECRET_KEY", "hr8U5zB2E407Rufi5_jfTY46YsX4PSBh")
BUCKET = "flatfiles"
PREFIX = "us_options_opra/day_aggs_v1"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = DATA_DIR / "slv_daily"
OUTPUT_DIR.mkdir(exist_ok=True)

START_DATE = date.today() - timedelta(days=730)
END_DATE = date.today()
TICKER_PREFIX = "O:SLV"


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )


def trading_days(start: date, end: date):
    """Generate weekdays between start and end (approximation of trading days)."""
    d = start
    while d <= end:
        if d.weekday() < 5:  # Mon-Fri
            yield d
        d += timedelta(days=1)


def download_and_filter_day(s3, day: date):
    """Download a day's flat file, filter for SLV, return list of row dicts."""
    key = f"{PREFIX}/{day.year}/{day.month:02d}/{day.isoformat()}.csv.gz"

    try:
        resp = s3.get_object(Bucket=BUCKET, Key=key)
    except s3.exceptions.NoSuchKey:
        return None

    compressed = resp["Body"].read()
    decompressed = gzip.decompress(compressed)
    reader = csv.DictReader(io.StringIO(decompressed.decode("utf-8")))

    slv_rows = [row for row in reader if row.get("ticker", "").startswith(TICKER_PREFIX)]
    return slv_rows


def main():
    print(f"Downloading SLV options flat files from {START_DATE} to {END_DATE}", flush=True)
    print(f"Output: {OUTPUT_DIR}", flush=True)
    print(flush=True)

    s3 = get_s3_client()

    # Check which days we already have
    existing = {f.stem for f in OUTPUT_DIR.glob("*.json")}

    days = list(trading_days(START_DATE, END_DATE))
    remaining = [d for d in days if d.isoformat() not in existing]

    print(f"Total trading days: {len(days)}", flush=True)
    print(f"Already downloaded: {len(existing)}", flush=True)
    print(f"Remaining: {len(remaining)}", flush=True)
    print(flush=True)

    total_rows = 0
    errors = []

    for i, day in enumerate(remaining):
        try:
            rows = download_and_filter_day(s3, day)
            if rows is None:
                print(f"  {day} — no file (holiday?)", flush=True)
                continue

            # Save day's SLV data
            out_file = OUTPUT_DIR / f"{day.isoformat()}.json"
            with open(out_file, "w") as f:
                json.dump(rows, f)

            total_rows += len(rows)

            if (i + 1) % 10 == 0 or i == len(remaining) - 1:
                print(f"  Progress: {i + 1}/{len(remaining)} days, {day}, {len(rows)} SLV contracts, {total_rows} total rows", flush=True)

        except Exception as e:
            errors.append({"date": day.isoformat(), "error": str(e)})
            print(f"  ERROR {day}: {e}", flush=True)

    print(f"\nDone!", flush=True)
    print(f"  Days downloaded: {len(remaining) - len(errors)}", flush=True)
    print(f"  Total SLV rows: {total_rows}", flush=True)
    print(f"  Errors: {len(errors)}", flush=True)

    if errors:
        with open(DATA_DIR / "flatfile_errors.json", "w") as f:
            json.dump(errors, f, indent=2)


if __name__ == "__main__":
    main()
