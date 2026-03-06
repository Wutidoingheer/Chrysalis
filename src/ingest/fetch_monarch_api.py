import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
import asyncio

RAW = Path("./data/raw")
RAW.mkdir(parents=True, exist_ok=True)

def _since_iso(days: int) -> str:
    dt = datetime.utcnow() - timedelta(days=max(1, days))
    return dt.strftime("%Y-%m-%d")

def save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

async def fetch_with_library_async(session_cookie: str | None, email: str | None, password: str | None, since_days: int):
    """Preferred: use monarchmoney-fork client if installed."""
    try:
        from monarchmoney import MonarchMoney
    except Exception as e:
        raise RuntimeError("monarchmoney library not installed. Install with: pip install -e ../monarchmoney-fork") from e

    mm = MonarchMoney()
    session_file = Path("./data/.monarch_session.json")

    # Try to load saved session first
    if session_file.exists():
        try:
            mm.load_session(str(session_file))
            print("[OK] Loaded saved session")
        except Exception as e:
            print(f"[WARN] Could not load saved session: {e}")

    # If session cookie provided, save it and load
    if session_cookie:
        try:
            # Save session cookie to file in format library expects
            session_data = {"session": session_cookie}
            session_file.write_text(json.dumps(session_data), encoding="utf-8")
            mm.load_session(str(session_file))
            print("[OK] Loaded session from cookie")
        except Exception as e:
            print(f"[WARN] Could not load session from cookie: {e}")

    # Otherwise login with credentials
    elif email and password:
        print("Logging in with email/password...")
        try:
            await mm.login(email=email, password=password, save_session=True)
            print("[OK] Login successful")
        except Exception as e:
            raise RuntimeError(f"Login failed: {e}")

    else:
        # Try to use saved session if available
        if not session_file.exists():
            raise ValueError("Provide MONARCH_SESSION_COOKIE or MONARCH_EMAIL+MONARCH_PASSWORD")

    # ---- Accounts ----
    print("Fetching accounts...")
    accounts_result = await mm.get_accounts()
    # Handle both dict and list responses
    if isinstance(accounts_result, dict):
        accounts = accounts_result.get("results", accounts_result.get("accounts", []))
    else:
        accounts = accounts_result
    print(f"Found {len(accounts)} accounts")

    # ---- Transactions ----
    print("Fetching transactions...")
    start_date = _since_iso(since_days)
    end_date = datetime.utcnow().strftime("%Y-%m-%d")  # Today's date
    all_txns = []
    limit = 500
    offset = 0
    
    while True:
        try:
            txns_result = await mm.get_transactions(
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset
            )
            # Handle both dict and list responses
            if isinstance(txns_result, dict):
                # Check for allTransactions at top level (GraphQL response format)
                if "allTransactions" in txns_result:
                    all_txns_data = txns_result["allTransactions"]
                    txns = all_txns_data.get("results", [])
                    total_count = all_txns_data.get("totalCount", len(txns))
                # Check for nested structure: data.allTransactions.results
                elif "data" in txns_result:
                    all_txns_data = txns_result["data"].get("allTransactions", {})
                    txns = all_txns_data.get("results", [])
                    total_count = all_txns_data.get("totalCount", len(txns))
                else:
                    txns = txns_result.get("results", txns_result.get("transactions", []))
                    total_count = txns_result.get("totalCount", len(txns))
            else:
                txns = txns_result
                total_count = len(txns) if isinstance(txns, list) else 0
            
            if not txns:
                break
            
            all_txns.extend(txns)
            offset += len(txns)
            
            print(f"  Fetched {len(all_txns)} transactions (offset: {offset})...")
            
            # Check if we've fetched all transactions
            if len(txns) < limit or (isinstance(txns_result, dict) and len(all_txns) >= total_count):
                break
                
            if offset > 50000:  # safety stop
                print("[WARN] Reached safety limit of 50,000 transactions")
                break
                
        except Exception as e:
            print(f"[ERROR] Error fetching transactions at offset {offset}: {e}")
            break

    save_json(RAW / "accounts.json", accounts)
    save_json(RAW / "transactions.json", all_txns)
    print(f"[OK] Wrote {RAW/'accounts.json'} ({len(accounts)} accounts)")
    print(f"[OK] Wrote {RAW/'transactions.json'} ({len(all_txns)} transactions)")

def fetch_with_library(session_cookie: str | None, email: str | None, password: str | None, since_days: int):
    """Synchronous wrapper for async fetch function."""
    asyncio.run(fetch_with_library_async(session_cookie, email, password, since_days))

def _headers():
    # Prefer a full raw header value if provided (e.g., "Token abc...", "Bearer abc...")
    auth_raw = os.environ.get("MONARCH_AUTHORIZATION")
    bearer = os.environ.get("MONARCH_BEARER")

    if not auth_raw and not bearer:
        raise RuntimeError("Set MONARCH_AUTHORIZATION (e.g., 'Token ...') or MONARCH_BEARER in .env")

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


    
if __name__ == "__main__":
    load_dotenv()
    session_cookie = os.getenv("MONARCH_SESSION_COOKIE") or None
    email = os.getenv("MONARCH_EMAIL") or None
    password = os.getenv("MONARCH_PASSWORD") or None
    since_days = int(os.getenv("MONARCH_SINCE_DAYS", "365"))

    fetch_with_library(session_cookie, email, password, since_days)
