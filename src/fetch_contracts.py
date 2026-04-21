"""Fetch and cache SLV options contracts list. Run this once before scheduling batch bar downloads."""

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


def api_get(url, params=None):
    for attempt in range(10):
        resp = requests.get(url, params=params)
        if resp.status_code == 429:
            wait = 65
            print(f"  Rate limited. Waiting {wait}s (attempt {attempt + 1})...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise Exception("Too many 429s")


def main():
    contracts_file = DATA_DIR / "slv_contracts.json"
    if contracts_file.exists():
        with open(contracts_file) as f:
            c = json.load(f)
        print(f"Already cached: {len(c)} contracts in {contracts_file}")
        return

    # Check for partial download to resume from
    partial_file = DATA_DIR / "slv_contracts_partial.json"
    contracts = []
    start_phase = "true"  # which expired phase to start from

    if partial_file.exists():
        with open(partial_file) as f:
            partial = json.load(f)
        contracts = partial.get("contracts", [])
        start_phase = partial.get("next_phase", "true")
        print(f"Resuming from partial: {len(contracts)} contracts, next phase: {start_phase}", flush=True)

    phases = ["true", "false"]
    if start_phase == "false":
        phases = ["false"]

    for expired in phases:
        label = "expired" if expired == "true" else "active"
        url = f"{BASE_URL}/v3/reference/options/contracts"
        params = {
            "underlying_ticker": "SLV",
            "expired": expired,
            "expiration_date.gte": START_DATE,
            "expiration_date.lte": END_DATE,
            "limit": 1000,
            "apiKey": API_KEY,
        }
        page = 1
        while url:
            data = api_get(url, params=params)
            results = data.get("results", [])
            contracts.extend(results)
            print(f"Page {page} ({label}): +{len(results)} (total: {len(contracts)})", flush=True)

            # Flush partial progress every page
            next_url = data.get("next_url")
            with open(partial_file, "w") as f:
                json.dump({
                    "contracts": contracts,
                    "next_phase": "false" if expired == "true" and not next_url else expired,
                }, f)

            if next_url:
                url = next_url
                params = {"apiKey": API_KEY}
            else:
                url = None
            page += 1
            time.sleep(13)

    with open(contracts_file, "w") as f:
        json.dump(contracts, f, indent=2)
    # Clean up partial file
    if partial_file.exists():
        partial_file.unlink()
    print(f"\nSaved {len(contracts)} contracts to {contracts_file}", flush=True)


if __name__ == "__main__":
    main()
