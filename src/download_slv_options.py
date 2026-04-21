"""
Download SLV options chain data from Massive.com (formerly Polygon.io).

Fetches daily OHLCV bars for all cached contracts over the full 2-year range.

Free tier limit: 5 requests/minute. Supports batch mode (--batch N).
"""

import argparse
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

import requests

API_KEY = os.environ.get("MASSIVE_API_KEY")
if not API_KEY:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    API_KEY = os.environ.get("MASSIVE_API_KEY")

BASE_URL = "https://api.polygon.io"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

END_DATE = date.today().isoformat()
START_DATE = (date.today() - timedelta(days=730)).isoformat()
TICKER = "SLV"

REQUEST_DELAY = 12


def api_get(url, params=None, max_retries=5):
    """Make an API request with retry on 429."""
    for attempt in range(max_retries):
        resp = requests.get(url, params=params)
        if resp.status_code == 429:
            wait = 60 * (attempt + 1)
            print(f"    Rate limited (429). Waiting {wait}s before retry {attempt + 1}/{max_retries}...", flush=True)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise Exception(f"Failed after {max_retries} retries due to rate limiting")


def get_all_contracts(contracts_path=None):
    """Load cached contracts list."""
    contracts_file = Path(contracts_path) if contracts_path else DATA_DIR / "slv_contracts.json"
    if not contracts_file.exists():
        raise FileNotFoundError(
            f"{contracts_file} not found. Run fetch_contracts.py first."
        )
    with open(contracts_file) as f:
        contracts = json.load(f)
    print(f"  Loaded {len(contracts)} contracts from {contracts_file.name}", flush=True)
    return contracts


def get_daily_bars(options_ticker: str):
    """Fetch daily OHLCV bars for a single options contract."""
    url = f"{BASE_URL}/v2/aggs/ticker/{options_ticker}/range/1/day/{START_DATE}/{END_DATE}"
    params = {"limit": 50000, "apiKey": API_KEY}
    data = api_get(url, params=params)
    return data.get("results", [])


def main(batch_size=0, contracts_path=None, output_name="slv_options_2yr.json"):
    print(f"Downloading SLV options data", flush=True)
    print(f"Date range: {START_DATE} to {END_DATE}", flush=True)
    print(f"API key: {API_KEY[:8]}...{API_KEY[-4:]}", flush=True)
    if batch_size:
        print(f"Batch mode: up to {batch_size} bar requests this run", flush=True)
    print(flush=True)

    # Step 1: Load contracts
    print("Step 1: Loading contracts...", flush=True)
    contracts = get_all_contracts(contracts_path)

    # Step 2: Download daily bars
    output_file = DATA_DIR / output_name
    if output_file.exists():
        with open(output_file) as f:
            all_bars = json.load(f)
        print(f"  Resuming from {len(all_bars)} previously downloaded", flush=True)
    else:
        all_bars = {}

    errors = []
    already_done = set(all_bars.keys())
    remaining = [c for c in contracts if c["ticker"] not in already_done]

    if not remaining:
        print("All contracts already downloaded!", flush=True)
        return

    to_process = remaining[:batch_size] if batch_size else remaining
    print(f"Step 2: Downloading bars for {len(to_process)} of {len(remaining)} remaining...", flush=True)

    for i, contract in enumerate(to_process):
        ticker = contract["ticker"]
        try:
            bars = get_daily_bars(ticker)
            if bars:
                all_bars[ticker] = {
                    "contract": contract,
                    "bars": bars,
                }
        except Exception as e:
            errors.append({"ticker": ticker, "error": str(e)})
            print(f"  ERROR on {ticker}: {e}", flush=True)

        # Flush to disk every 5 contracts
        if (i + 1) % 5 == 0 or i == len(to_process) - 1:
            with open(output_file, "w") as f:
                json.dump(all_bars, f)
            print(f"  Progress: {i + 1}/{len(to_process)} this run, {len(all_bars)} total with data [saved]", flush=True)

        time.sleep(REQUEST_DELAY)

    # Final save
    with open(output_file, "w") as f:
        json.dump(all_bars, f)
    print(f"\nSaved {len(all_bars)} contracts to {output_file}", flush=True)

    if errors:
        errors_file = DATA_DIR / "slv_download_errors.json"
        with open(errors_file, "w") as f:
            json.dump(errors, f, indent=2)
        print(f"Saved {len(errors)} errors to {errors_file}", flush=True)

    still_remaining = len(remaining) - len(to_process) + len(errors)
    total_bars = sum(len(v["bars"]) for v in all_bars.values())
    print(f"\nSummary:", flush=True)
    print(f"  Contracts total: {len(contracts)}", flush=True)
    print(f"  Downloaded this run: {len(to_process) - len(errors)}", flush=True)
    print(f"  Total with data: {len(all_bars)}", flush=True)
    print(f"  Still remaining: {still_remaining}", flush=True)
    print(f"  Total daily bars: {total_bars}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download SLV options chain data")
    parser.add_argument("--batch", type=int, default=0,
                        help="Max bar requests per invocation (0 = unlimited)")
    parser.add_argument("--contracts", type=str, default=None,
                        help="Path to contracts JSON file (default: data/slv_contracts.json)")
    parser.add_argument("--output", type=str, default="slv_options_2yr.json",
                        help="Output filename in data/ dir")
    args = parser.parse_args()
    main(batch_size=args.batch, contracts_path=args.contracts, output_name=args.output)
