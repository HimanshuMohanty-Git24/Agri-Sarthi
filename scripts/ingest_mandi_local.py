"""
Fetch live mandi prices from data.gov.in locally and push to Databricks Delta table.
This bypasses Databricks serverless outbound restrictions on data.gov.in.
"""
import requests
import json
import time
from datetime import datetime

from dotenv import load_dotenv
import os

load_dotenv()

# ─── Config ──────────────────────────────────────────────────────────
DATAGOV_KEY = os.getenv("DATAGOV_API_KEY", "")
DATAGOV_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "")
SQL_WAREHOUSE_ID = os.getenv("DATABRICKS_SQL_WAREHOUSE_ID", "")

if not all([DATAGOV_KEY, DATABRICKS_HOST, DATABRICKS_TOKEN, SQL_WAREHOUSE_ID]):
    print("ERROR: Set DATAGOV_API_KEY, DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_SQL_WAREHOUSE_ID in .env")
    exit(1)

HEADERS = {"Authorization": f"Bearer {DATABRICKS_TOKEN}"}


def run_sql(statement, wait="30s"):
    """Execute SQL via Databricks SQL Statement API."""
    resp = requests.post(
        f"{DATABRICKS_HOST}/api/2.0/sql/statements",
        headers=HEADERS,
        json={
            "warehouse_id": SQL_WAREHOUSE_ID,
            "statement": statement,
            "wait_timeout": wait,
        },
    )
    data = resp.json()
    status = data.get("status", {}).get("state", "")
    if status == "FAILED":
        error = data.get("status", {}).get("error", {}).get("message", "Unknown")
        print(f"  SQL Error: {error}")
    return data


def fetch_all_prices():
    """Fetch all available mandi prices from data.gov.in (public key: 10 per request)."""
    all_records = []

    # Key commodities to fetch
    COMMODITIES = [
        "Wheat", "Rice", "Potato", "Tomato", "Onion",
        "Soybean", "Cotton", "Mustard", "Sugarcane", "Maize",
        "Jowar", "Bajra", "Groundnut", "Tur", "Urad",
        "Moong", "Chana", "Masoor", "Banana", "Turmeric",
        "Chilli", "Garlic", "Ginger", "Coconut", "Apple",
        "Mango", "Grapes", "Lemon", "Arhar", "Sorghum",
        "Paddy(Dhan)(Common)", "Ragi", "Arecanut",
    ]

    # Key states for broader coverage
    STATES = [
        "Punjab", "Haryana", "Uttar Pradesh", "Madhya Pradesh",
        "Rajasthan", "Maharashtra", "Karnataka", "Tamil Nadu",
        "Andhra Pradesh", "Telangana", "Gujarat", "Bihar",
        "West Bengal", "Odisha", "Kerala",
    ]

    print(f"📡 Fetching live mandi prices from data.gov.in (paginated)...")

    # Strategy 1: Fetch by commodity (10 records per request, paginate up to 50 per commodity)
    for commodity in COMMODITIES:
        for page_offset in range(0, 50, 10):
            try:
                params = {
                    "api-key": DATAGOV_KEY,
                    "format": "json",
                    "limit": 10,
                    "offset": page_offset,
                    "filters[commodity]": commodity,
                }
                response = requests.get(DATAGOV_URL, params=params, timeout=20)
                if response.status_code == 200:
                    data = response.json()
                    records = data.get("records", [])
                    if not records:
                        break
                    for record in records:
                        rec = _parse_record(record)
                        if rec:
                            all_records.append(rec)
                    if len(records) < 10:
                        break
                else:
                    break
            except Exception:
                break
        count = len([r for r in all_records if r["crop_name"].lower() == commodity.lower()])
        if count > 0:
            print(f"   ✅ {commodity}: {count} records")

    # Strategy 2: Fetch by state to get diverse commodity coverage
    for state in STATES:
        for page_offset in range(0, 50, 10):
            try:
                params = {
                    "api-key": DATAGOV_KEY,
                    "format": "json",
                    "limit": 10,
                    "offset": page_offset,
                    "filters[state]": state,
                }
                response = requests.get(DATAGOV_URL, params=params, timeout=20)
                if response.status_code == 200:
                    records = response.json().get("records", [])
                    if not records:
                        break
                    for record in records:
                        rec = _parse_record(record)
                        if rec:
                            all_records.append(rec)
                    if len(records) < 10:
                        break
                else:
                    break
            except Exception:
                break

    # Strategy 3: Bulk fetch without filters (get whatever is available)
    for page_offset in range(0, 200, 10):
        try:
            params = {
                "api-key": DATAGOV_KEY,
                "format": "json",
                "limit": 10,
                "offset": page_offset,
            }
            response = requests.get(DATAGOV_URL, params=params, timeout=20)
            if response.status_code == 200:
                records = response.json().get("records", [])
                if not records:
                    break
                for record in records:
                    rec = _parse_record(record)
                    if rec:
                        all_records.append(rec)
                if len(records) < 10:
                    break
            else:
                break
        except Exception:
            break

    print(f"\n📊 Total records fetched (before dedup): {len(all_records)}")
    return all_records


def _parse_record(record):
    """Parse a single API record into our schema."""
    try:
        min_p = float(record.get("min_price", 0))
        max_p = float(record.get("max_price", 0))
        modal_p = float(record.get("modal_price", 0))
    except (ValueError, TypeError):
        return None

    if min_p <= 0 or max_p <= 0 or modal_p <= 0:
        return None

    raw_date = record.get("arrival_date", "")
    try:
        parsed_date = datetime.strptime(raw_date, "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        parsed_date = raw_date

    return {
        "crop_name": record.get("commodity", "").strip().replace("'", "''"),
        "state": record.get("state", "").strip().replace("'", "''"),
        "district": record.get("district", "").strip().replace("'", "''"),
        "market": record.get("market", "").strip().replace("'", "''"),
        "min_price": min_p,
        "max_price": max_p,
        "modal_price": modal_p,
        "unit": "Quintal",
        "arrival_date": parsed_date,
    }


def deduplicate(records):
    """Remove duplicates based on crop_name + market + arrival_date."""
    seen = set()
    unique = []
    for r in records:
        key = (r["crop_name"], r["market"], r["arrival_date"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def insert_to_databricks(records, batch_size=100):
    """Insert records into Delta table using SQL INSERT statements."""
    print(f"\n📤 Inserting {len(records)} records into agrisarthi.main.mandi_prices...")

    # First, clear old data that will be replaced
    dates = list(set(r["arrival_date"] for r in records))
    if dates:
        date_list = ", ".join(f"'{d}'" for d in dates)
        print(f"   Clearing existing data for dates: {dates[:3]}...")
        run_sql(f"DELETE FROM agrisarthi.main.mandi_prices WHERE arrival_date IN ({date_list})")
        time.sleep(2)

    # Insert in batches
    total_inserted = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        values = []
        for r in batch:
            values.append(
                f"('{r['crop_name']}', '{r['state']}', '{r['district']}', "
                f"'{r['market']}', {r['min_price']}, {r['max_price']}, "
                f"{r['modal_price']}, '{r['unit']}', '{r['arrival_date']}')"
            )

        sql = (
            "INSERT INTO agrisarthi.main.mandi_prices "
            "(crop_name, state, district, market, min_price, max_price, modal_price, unit, arrival_date) "
            "VALUES " + ", ".join(values)
        )

        result = run_sql(sql)
        status = result.get("status", {}).get("state", "")

        if status == "FAILED":
            print(f"  ❌ Batch {i//batch_size + 1} failed")
            # Try smaller batches
            for r in batch:
                single_sql = (
                    "INSERT INTO agrisarthi.main.mandi_prices "
                    "(crop_name, state, district, market, min_price, max_price, modal_price, unit, arrival_date) "
                    f"VALUES ('{r['crop_name']}', '{r['state']}', '{r['district']}', "
                    f"'{r['market']}', {r['min_price']}, {r['max_price']}, "
                    f"{r['modal_price']}, '{r['unit']}', '{r['arrival_date']}')"
                )
                sr = run_sql(single_sql)
                if sr.get("status", {}).get("state") != "FAILED":
                    total_inserted += 1
        else:
            total_inserted += len(batch)

        print(f"   Inserted batch {i//batch_size + 1}: {total_inserted}/{len(records)} records")
        time.sleep(0.5)  # Avoid rate limits

    return total_inserted


def verify():
    """Check final state of the table."""
    print("\n📊 Verifying mandi_prices table...")

    r = run_sql("SELECT COUNT(*) FROM agrisarthi.main.mandi_prices")
    total = r.get("result", {}).get("data_array", [[0]])[0][0]
    print(f"   Total records: {total}")

    r = run_sql(
        "SELECT arrival_date, COUNT(*) as cnt FROM agrisarthi.main.mandi_prices "
        "GROUP BY arrival_date ORDER BY arrival_date DESC LIMIT 5"
    )
    print("   By date:")
    for row in r.get("result", {}).get("data_array", []):
        print(f"     {row[0]}: {row[1]} records")

    r = run_sql(
        "SELECT crop_name, COUNT(*) as markets, ROUND(AVG(modal_price)) as avg_price "
        "FROM agrisarthi.main.mandi_prices GROUP BY crop_name ORDER BY markets DESC LIMIT 10"
    )
    print("   Top commodities:")
    for row in r.get("result", {}).get("data_array", []):
        print(f"     {row[0]}: {row[1]} markets, avg Rs.{row[2]}")

    # Wheat in Punjab
    r = run_sql(
        "SELECT crop_name, state, market, modal_price, arrival_date "
        "FROM agrisarthi.main.mandi_prices "
        "WHERE LOWER(crop_name) LIKE '%wheat%' AND LOWER(state) LIKE '%punjab%' "
        "ORDER BY arrival_date DESC LIMIT 5"
    )
    print("   Wheat in Punjab:")
    for row in r.get("result", {}).get("data_array", []):
        print(f"     {row[2]}: Rs.{row[3]} on {row[4]}")


if __name__ == "__main__":
    # Step 1: Fetch from API
    records = fetch_all_prices()

    if records:
        # Step 2: Deduplicate
        records = deduplicate(records)
        print(f"📊 After dedup: {len(records)} unique records")

        # Step 3: Insert into Databricks
        inserted = insert_to_databricks(records)
        print(f"\n✅ Inserted {inserted} records")

        # Step 4: Verify
        verify()
    else:
        print("❌ No records fetched from API")
