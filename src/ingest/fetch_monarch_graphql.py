# src/ingest/fetch_monarch_graphql.py
import os, json
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

RAW = Path("./data/raw"); RAW.mkdir(parents=True, exist_ok=True)
API = "https://api.monarchmoney.com/graphql"  # GraphQL endpoint the web app uses

def _iso(dt): return dt.strftime("%Y-%m-%d")

def _headers():
    """
    Prefer a full Authorization header from .env:
      MONARCH_AUTHORIZATION="Token abc..."  (or "Bearer abc...")
    Fallback to:
      MONARCH_BEARER="abc..."  (we'll prefix 'Bearer ')
    Optional:
      MONARCH_DEVICE_UUID for stricter header parity with browser.
    """
    auth_raw = os.environ.get("MONARCH_AUTHORIZATION")
    bearer = os.environ.get("MONARCH_BEARER")
    if not auth_raw and not bearer:
        raise RuntimeError("Set MONARCH_AUTHORIZATION (e.g., 'Token abc...') or MONARCH_BEARER in .env")

    h = {
        "Authorization": auth_raw if auth_raw else f"Bearer {bearer}",
        "Content-Type": "application/json",
        "Origin": "https://app.monarchmoney.com",
        "Referer": "https://app.monarchmoney.com/",
        "User-Agent": "Mozilla/5.0",
    }
    dev = os.environ.get("MONARCH_DEVICE_UUID")
    if dev:
        h["monarchDeviceUUID"] = dev
    return h

def gql(query: str, variables: dict | None = None):
    r = requests.post(API, json={"query": query, "variables": variables or {}}, headers=_headers(), timeout=30)
    if r.status_code in (401, 403):
        raise RuntimeError("Auth failed (401/403). Refresh your token from DevTools and update .env")
    if r.status_code == 404:
        raise RuntimeError("Endpoint 404. If your app uses a different host/path, tell me and we’ll update API URL.")
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]

def fetch_all(since_days: int = 365):
    today = datetime.utcnow()
    start = _iso(today - timedelta(days=max(1, since_days)))
    end   = _iso(today)

    # --- Accounts ---
    q_accounts = """
    query {
      GetAccounts {
        id
        name
        institutionName
        type
        currentBalance
        availableBalance
        lastUpdated
      }
    }"""
    accounts = gql(q_accounts)["GetAccounts"]

    # --- Transactions (paged) ---
    all_tx = []
    limit, offset = 500, 0
    q_tx = """
    query($start:String!, $end:String!, $limit:Int!, $offset:Int!) {
      GetTransactions(startDate:$start, endDate:$end, limit:$limit, offset:$offset) {
        id
        date
        amount
        description
        merchant
        accountName
        categoryName
        createdAt
        updatedAt
      }
    }"""
    while True:
        chunk = gql(q_tx, {"start": start, "end": end, "limit": limit, "offset": offset})["GetTransactions"]
        if not chunk:
            break
        all_tx.extend(chunk)
        offset += len(chunk)
        if len(chunk) < limit:
            break

    (RAW / "accounts.json").write_text(json.dumps(accounts, indent=2), encoding="utf-8")
    (RAW / "transactions.json").write_text(json.dumps(all_tx, indent=2), encoding="utf-8")
    print(f"Wrote {RAW/'accounts.json'} ({len(accounts)} accounts)")
    print(f"Wrote {RAW/'transactions.json'} ({len(all_tx)} transactions)")

if __name__ == "__main__":
    load_dotenv()
    days = int(os.environ.get("MONARCH_SINCE_DAYS", "365"))
    fetch_all(days)
