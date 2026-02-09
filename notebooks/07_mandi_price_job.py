"""
AgriSarthi v2 — Mandi Price Ingestion Job
Scheduled Databricks job to pull fresh market prices from data.gov.in API.

Databricks tech used: Delta Lake, Serverless Compute, Unity Catalog
Run as: Databricks Workflow (daily at 6 AM IST)
"""

# COMMAND ----------

# MAGIC %md
# MAGIC # 📈 AgriSarthi — Mandi Price Refresh Job
# MAGIC 
# MAGIC Pulls latest mandi prices from the Government of India's Open Data API
# MAGIC and upserts into the Delta Lake table.

# COMMAND ----------

import requests
import json
from datetime import datetime
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

# COMMAND ----------

# ─── Pull from data.gov.in API ──────────────────────────────────────
# Resource: Current daily prices of various commodities from various markets
# This is the LIVE government API updated daily

API_KEY = dbutils.secrets.get(scope="agrisarthi", key="datagov-api-key")
BASE_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

# Commodities to track (major Indian agricultural commodities)
COMMODITIES = [
    "Wheat", "Rice", "Potato", "Tomato", "Onion",
    "Soybean", "Cotton", "Mustard", "Sugarcane", "Maize",
    "Jowar", "Bajra", "Groundnut", "Tur", "Urad",
    "Moong", "Chana", "Arhar", "Masoor", "Banana",
    "Turmeric", "Chilli", "Garlic", "Ginger", "Coconut",
    "Black pepper", "Cardamom", "Tea", "Coffee", "Rubber",
    "Jute", "Lemon", "Apple", "Mango", "Grapes"
]

all_records = []
today_str = datetime.now().strftime("%d/%m/%Y")

# First: pull ALL records without commodity filter (more efficient)
print(f"📡 Fetching all live mandi prices from data.gov.in...")
print(f"   Date: {today_str}")

try:
    offset = 0
    batch_size = 500
    max_records = 5000
    
    while offset < max_records:
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": batch_size,
            "offset": offset,
        }
        
        response = requests.get(BASE_URL, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            records = data.get("records", [])
            total_available = data.get("total", 0)
            
            if not records:
                break
            
            for record in records:
                try:
                    min_p = float(record.get("min_price", 0))
                    max_p = float(record.get("max_price", 0))
                    modal_p = float(record.get("modal_price", 0))
                except (ValueError, TypeError):
                    continue
                
                if min_p <= 0 or max_p <= 0 or modal_p <= 0:
                    continue
                
                # Convert date from DD/MM/YYYY to YYYY-MM-DD
                raw_date = record.get("arrival_date", "")
                try:
                    parsed_date = datetime.strptime(raw_date, "%d/%m/%Y").strftime("%Y-%m-%d")
                except:
                    parsed_date = raw_date
                
                all_records.append({
                    "crop_name": record.get("commodity", "").strip(),
                    "state": record.get("state", "").strip(),
                    "district": record.get("district", "").strip(),
                    "market": record.get("market", "").strip(),
                    "min_price": min_p,
                    "max_price": max_p,
                    "modal_price": modal_p,
                    "unit": "Quintal",
                    "arrival_date": parsed_date,
                })
            
            fetched_so_far = offset + len(records)
            print(f"   Fetched {fetched_so_far} of {total_available} available records")
            offset += batch_size
            
            if len(records) < batch_size:
                break  # No more records
        else:
            print(f"⚠️ API returned HTTP {response.status_code}")
            break
            
except Exception as e:
    import traceback
    print(f"❌ Error fetching from data.gov.in: {e}")
    traceback.print_exc()

status_msg = f"Bulk fetch: {len(all_records)} records"
print(f"\n📊 Total valid records fetched: {len(all_records)}")

# Also pull commodity-specific data for our key crops
print(f"\n📡 Fetching targeted data for key commodities...")
for commodity in COMMODITIES[:20]:
    try:
        params = {
            "api-key": API_KEY,
            "format": "json",
            "filters[commodity]": commodity,
            "limit": 100,
            "sort[arrival_date]": "desc",
        }
        
        response = requests.get(BASE_URL, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            records = data.get("records", [])
            count = 0
            
            for record in records:
                try:
                    min_p = float(record.get("min_price", 0))
                    max_p = float(record.get("max_price", 0))
                    modal_p = float(record.get("modal_price", 0))
                except (ValueError, TypeError):
                    continue
                
                if min_p <= 0 or max_p <= 0 or modal_p <= 0:
                    continue
                
                raw_date = record.get("arrival_date", "")
                try:
                    parsed_date = datetime.strptime(raw_date, "%d/%m/%Y").strftime("%Y-%m-%d")
                except:
                    parsed_date = raw_date
                
                all_records.append({
                    "crop_name": record.get("commodity", "").strip(),
                    "state": record.get("state", "").strip(),
                    "district": record.get("district", "").strip(),
                    "market": record.get("market", "").strip(),
                    "min_price": min_p,
                    "max_price": max_p,
                    "modal_price": modal_p,
                    "unit": "Quintal",
                    "arrival_date": parsed_date,
                })
                count += 1
            
            if count > 0:
                print(f"   ✅ {commodity}: {count} records")
        
    except Exception as e:
        print(f"   ❌ {commodity}: {e}")

print(f"\n📊 Total records (including targeted): {len(all_records)}")

# COMMAND ----------

# ─── Deduplicate and Upsert into Delta Table ────────────────────────

if all_records:
    schema = StructType([
        StructField("crop_name", StringType(), True),
        StructField("state", StringType(), True),
        StructField("district", StringType(), True),
        StructField("market", StringType(), True),
        StructField("min_price", DoubleType(), True),
        StructField("max_price", DoubleType(), True),
        StructField("modal_price", DoubleType(), True),
        StructField("unit", StringType(), True),
        StructField("arrival_date", StringType(), True),
    ])
    
    new_prices_df = spark.createDataFrame(all_records, schema=schema)
    
    # Remove duplicates (same crop + market + date)
    new_prices_df = new_prices_df.dropDuplicates(["crop_name", "market", "arrival_date"])
    
    # Filter valid data
    new_prices_df = new_prices_df.filter(
        (F.col("min_price") > 0) & 
        (F.col("max_price") > 0) &
        (F.col("crop_name").isNotNull()) &
        (F.col("state").isNotNull()) &
        (F.col("crop_name") != "")
    )
    
    deduped_count = new_prices_df.count()
    print(f"📊 After dedup: {deduped_count} unique records")
    
    # Write with merge (upsert)
    new_prices_df.createOrReplaceTempView("new_prices")
    
    spark.sql("""
        MERGE INTO agrisarthi.main.mandi_prices AS target
        USING new_prices AS source
        ON target.crop_name = source.crop_name 
           AND target.market = source.market 
           AND target.arrival_date = source.arrival_date
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)
    
    final_count = spark.table("agrisarthi.main.mandi_prices").count()
    print(f"✅ Mandi prices updated! Total records in table: {final_count}")
    
    # Show summary
    summary = spark.sql("""
        SELECT crop_name, COUNT(*) as markets, 
               ROUND(AVG(modal_price), 0) as avg_modal_price,
               MAX(arrival_date) as latest_date
        FROM agrisarthi.main.mandi_prices
        GROUP BY crop_name
        ORDER BY markets DESC
        LIMIT 20
    """)
    summary.show(20, truncate=False)
else:
    print("⚠️ No new records to ingest")

# COMMAND ----------

# ─── Verify latest prices ──────────────────────────────────────────

latest = spark.sql("""
    SELECT crop_name, state, market, modal_price, arrival_date
    FROM agrisarthi.main.mandi_prices
    ORDER BY arrival_date DESC
    LIMIT 20
""")
latest.show(20, truncate=False)

total_final = spark.table("agrisarthi.main.mandi_prices").count()
dbutils.notebook.exit(f"Done. Total records: {total_final}. {status_msg}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Mandi Price Refresh Complete!
# MAGIC 
# MAGIC **Data Source:** Government of India Open Data API (`data.gov.in`)
# MAGIC 
# MAGIC **Schedule this as a Databricks Workflow:**
# MAGIC 1. Go to **Workflows** → **Create Job**
# MAGIC 2. Add this notebook as a task
# MAGIC 3. Set schedule: `0 0 6 * * ?` (daily at 6 AM IST)  
# MAGIC 4. Cluster: Serverless
# MAGIC 
# MAGIC The Delta table `agrisarthi.main.mandi_prices` is used directly by the
# MAGIC `market_price_tool` in the agent.
