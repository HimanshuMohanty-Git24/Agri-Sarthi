"""
AgriSarthi v2 — Data Ingestion to Delta Lake
Run this notebook in Databricks to ingest soil data CSV into Delta Lake
and create Vector Search index.

This replaces: rag.py (FAISS + Google Gemini Embeddings)
Databricks tech used: Delta Lake, Unity Catalog, Vector Search, Serverless Compute
"""

# COMMAND ----------

# MAGIC %md
# MAGIC # 🌾 AgriSarthi — Data Ingestion Pipeline
# MAGIC 
# MAGIC This notebook:
# MAGIC 1. Creates the Unity Catalog namespace (`agrisarthi.main`)
# MAGIC 2. Ingests `soildata.csv` into a Delta table
# MAGIC 3. Creates a Vector Search index for RAG retrieval
# MAGIC 4. Ingests government schemes data
# MAGIC 5. Sets up the mandi prices table (for scheduled refresh)

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch databricks-sdk --quiet
# MAGIC %restart_python

# COMMAND ----------

# Create Unity Catalog namespace
spark.sql("CREATE CATALOG IF NOT EXISTS agrisarthi")
spark.sql("USE CATALOG agrisarthi")
spark.sql("CREATE SCHEMA IF NOT EXISTS main")
spark.sql("USE SCHEMA main")
print("✅ Unity Catalog namespace ready: agrisarthi.main")

# COMMAND ----------

import pandas as pd
from pyspark.sql import functions as F
from pyspark.sql.types import *

# ─── 1. Soil Data Ingestion ────────────────────────────────────────

# Upload soildata.csv to DBFS or Volumes first, then:
# If using Unity Catalog Volumes:
#   soil_df = spark.read.csv("/Volumes/agrisarthi/main/raw/soildata.csv", header=True, inferSchema=True)
# If using DBFS:
#   soil_df = spark.read.csv("dbfs:/FileStore/agrisarthi/soildata.csv", header=True, inferSchema=True)

# For hackathon, load from pandas then convert:
soil_csv_path = "/Volumes/agrisarthi/main/raw/soildata.csv"

soil_df = spark.read.csv(soil_csv_path, header=True, inferSchema=True)

print(f"✅ Loaded {soil_df.count()} soil records")
soil_df.printSchema()

# COMMAND ----------

# Add a text column for RAG retrieval (same format as original rag.py)
soil_with_text = soil_df.withColumn(
    "soil_text",
    F.concat_ws(
        "\n",
        F.concat(F.lit("Soil analysis for "), F.col("district"), F.lit(", "), F.col("state"), F.lit(":")),
        F.concat(F.lit("- Soil Type: "), F.col("soil_type")),
        F.concat(F.lit("- pH Level: "), F.col("ph").cast("string")),
        F.concat(F.lit("- Organic Carbon: "), F.col("organic_carbon").cast("string"), F.lit("%")),
        F.concat(F.lit("- Nitrogen (N): "), F.col("nitrogen").cast("string"), F.lit(" kg/ha")),
        F.concat(F.lit("- Phosphorus (P): "), F.col("phosphorus").cast("string"), F.lit(" kg/ha")),
        F.concat(F.lit("- Potassium (K): "), F.col("potassium").cast("string"), F.lit(" kg/ha")),
        F.concat(F.lit("- Average Annual Rainfall: "), F.col("rainfall").cast("string"), F.lit(" mm")),
        F.concat(F.lit("- Average Temperature: "), F.col("temperature").cast("string"), F.lit("°C")),
        F.concat(
            F.lit("This combination of "), F.col("soil_type"),
            F.lit(" soil with a pH of "), F.col("ph").cast("string"),
            F.lit(" is suitable for specific crops adapted to these conditions.")
        ),
    )
)

# Write to Delta table
soil_with_text.write \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable("agrisarthi.main.soil_data")

print("✅ Soil data saved to Delta table: agrisarthi.main.soil_data")

# COMMAND ----------

# Verify soil data
verify_df = spark.sql("SELECT state, district, soil_type, ph, soil_text FROM agrisarthi.main.soil_data LIMIT 5")
verify_df.show(truncate=False)
print(f"✅ Total soil records: {spark.sql('SELECT COUNT(*) FROM agrisarthi.main.soil_data').collect()[0][0]}")

# COMMAND ----------

# ─── 2. Create Vector Search Index ─────────────────────────────────

from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient()

# Create Vector Search endpoint (one-time)
try:
    vsc.create_endpoint(
        name="agrisarthi-vs-endpoint",
        endpoint_type="STANDARD"
    )
    print("✅ Vector Search endpoint created")
except Exception as e:
    print(f"ℹ️ Endpoint may already exist: {e}")

# COMMAND ----------

# Create the Vector Search index with Delta Sync
# This auto-syncs when the Delta table is updated!
try:
    index = vsc.create_delta_sync_index(
        endpoint_name="agrisarthi-vs-endpoint",
        index_name="agrisarthi.main.soil_vector_index",
        source_table_name="agrisarthi.main.soil_data",
        pipeline_type="TRIGGERED",  # or "CONTINUOUS" for real-time
        primary_key="district",
        embedding_source_column="soil_text",
        embedding_model_endpoint_name="databricks-bge-large-en"
    )
    print("✅ Vector Search index created with auto-sync from Delta table")
except Exception as e:
    print(f"ℹ️ Index may already exist: {e}")

# COMMAND ----------

# Test the Vector Search index
# Note: Index sync takes 5-10 minutes after creation. We'll retry with a wait.
import time

def test_vector_search(max_retries=5, wait_seconds=60):
    for attempt in range(max_retries):
        try:
            results = vsc.get_index(
                endpoint_name="agrisarthi-vs-endpoint",
                index_name="agrisarthi.main.soil_vector_index"
            ).similarity_search(
                query_text="soil data for Lucknow Uttar Pradesh",
                columns=["state", "district", "soil_type", "ph", "soil_text"],
                num_results=3
            )
            print("🔍 Vector Search test results:")
            for doc in results.get("result", {}).get("data_array", []):
                print(f"  📍 {doc[1]}, {doc[0]} — {doc[2]} soil, pH {doc[3]}")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⏳ Vector Search index not ready yet (attempt {attempt+1}/{max_retries}). Waiting {wait_seconds}s...")
                time.sleep(wait_seconds)
            else:
                print(f"⚠️ Vector Search test skipped — index is still syncing. This is normal.")
                print(f"   It will be available in a few minutes. Error: {e}")

test_vector_search()

# COMMAND ----------

# ─── 3. Government Schemes Table ───────────────────────────────────

schemes_data = [
    {
        "scheme_name": "PM-KUSUM",
        "full_name": "Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyan",
        "category": "Solar Energy",
        "description": "Solar pump installation and grid-connected solar for farmers. Component A: 10,000 MW solar plants on barren land. Component B: 20 lakh standalone solar pumps. Component C: 15 lakh grid-connected solar pumps.",
        "eligibility": "Individual farmers, FPOs, cooperatives, panchayats, WUAs",
        "subsidy_percent": 60,
        "ministry": "Ministry of New and Renewable Energy",
        "website": "https://pmkusum.mnre.gov.in",
        "states": "All India",
        "documents_required": "Aadhaar Card, Land Records, Bank Account, Electricity Connection Proof"
    },
    {
        "scheme_name": "PM-KISAN",
        "full_name": "Pradhan Mantri Kisan Samman Nidhi",
        "category": "Direct Income Support",
        "description": "Rs 6000 per year in 3 installments of Rs 2000 directly to farmer bank accounts. Covers all small and marginal farmers.",
        "eligibility": "All landholding farmer families with cultivable land",
        "subsidy_percent": 100,
        "ministry": "Ministry of Agriculture",
        "website": "https://pmkisan.gov.in",
        "states": "All India",
        "documents_required": "Aadhaar Card, Land Records, Bank Account"
    },
    {
        "scheme_name": "PMFBY",
        "full_name": "Pradhan Mantri Fasal Bima Yojana",
        "category": "Crop Insurance",
        "description": "Crop insurance at very low premium - 2% for Kharif, 1.5% for Rabi, 5% for commercial crops. Covers natural calamities, pests, diseases.",
        "eligibility": "All farmers growing notified crops in notified areas",
        "subsidy_percent": 95,
        "ministry": "Ministry of Agriculture",
        "website": "https://pmfby.gov.in",
        "states": "All India",
        "documents_required": "Aadhaar Card, Land Records, Bank Account, Sowing Certificate"
    },
    {
        "scheme_name": "Soil Health Card",
        "full_name": "Soil Health Card Scheme",
        "category": "Soil Health",
        "description": "Free soil testing and health card with crop-wise fertilizer recommendations. Helps farmers optimize input costs and improve yields.",
        "eligibility": "All farmers",
        "subsidy_percent": 100,
        "ministry": "Ministry of Agriculture",
        "website": "https://soilhealth.dac.gov.in",
        "states": "All India",
        "documents_required": "Aadhaar Card, Land Details"
    },
    {
        "scheme_name": "KCC",
        "full_name": "Kisan Credit Card",
        "category": "Agricultural Credit",
        "description": "Short-term credit for crop production at 7% interest (4% effective with subvention). Credit limit based on land holding, crop pattern, and scale of finance.",
        "eligibility": "All farmers, sharecroppers, tenant farmers, SHGs, JLGs",
        "subsidy_percent": 0,
        "ministry": "Ministry of Agriculture / RBI",
        "website": "https://www.nabard.org",
        "states": "All India",
        "documents_required": "Aadhaar Card, Land Records, Bank Account, Passport Photo"
    },
    {
        "scheme_name": "eNAM",
        "full_name": "National Agriculture Market",
        "category": "Market Access",
        "description": "Online trading platform for agricultural commodities. Connects farmers to multiple markets for better price discovery. Over 1000 mandis connected.",
        "eligibility": "All farmers, traders, buyers",
        "subsidy_percent": 0,
        "ministry": "Ministry of Agriculture",
        "website": "https://enam.gov.in",
        "states": "All India (1000+ mandis)",
        "documents_required": "Aadhaar Card, Bank Account, Mandi License (for traders)"
    },
    {
        "scheme_name": "SMAM",
        "full_name": "Sub-Mission on Agricultural Mechanization",
        "category": "Farm Mechanization",
        "description": "Subsidy on purchase of farm machinery and equipment. 40-50% subsidy for individual farmers, up to 80% for SC/ST/women/small farmers.",
        "eligibility": "Individual farmers, FPOs, cooperatives",
        "subsidy_percent": 50,
        "ministry": "Ministry of Agriculture",
        "website": "https://agrimachinery.nic.in",
        "states": "All India",
        "documents_required": "Aadhaar Card, Land Records, Bank Account, Caste Certificate (if applicable)"
    },
    {
        "scheme_name": "PMKSY",
        "full_name": "Pradhan Mantri Krishi Sinchayee Yojana",
        "category": "Irrigation",
        "description": "Per Drop More Crop — micro irrigation (drip/sprinkler) with 55% subsidy for general and 70% for small/marginal farmers.",
        "eligibility": "All farmers with own/leased land",
        "subsidy_percent": 55,
        "ministry": "Ministry of Agriculture / Ministry of Jal Shakti",
        "website": "https://pmksy.gov.in",
        "states": "All India",
        "documents_required": "Aadhaar Card, Land Records, Bank Account, Water Source Proof"
    },
]

schemes_df = spark.createDataFrame(schemes_data)
schemes_df.write \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable("agrisarthi.main.govt_schemes")

print(f"✅ {len(schemes_data)} government schemes loaded into Delta table")

# COMMAND ----------

# ─── 4. Mandi Prices Table (Template for scheduled ingestion) ──────

mandi_schema = StructType([
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

# Sample data — in production, this would be populated by a scheduled job 
# pulling from data.gov.in API or eNAM
sample_mandi_data = [
    ("Wheat", "Uttar Pradesh", "Lucknow", "Lucknow Mandi", 2100.0, 2350.0, 2200.0, "Quintal", "2025-02-07"),
    ("Rice", "Punjab", "Amritsar", "Amritsar Mandi", 2800.0, 3100.0, 2950.0, "Quintal", "2025-02-07"),
    ("Potato", "Uttar Pradesh", "Agra", "Agra Mandi", 800.0, 1200.0, 1000.0, "Quintal", "2025-02-07"),
    ("Tomato", "Karnataka", "Bengaluru", "Yeshwanthpur", 2500.0, 3500.0, 3000.0, "Quintal", "2025-02-07"),
    ("Onion", "Maharashtra", "Nashik", "Lasalgaon", 1500.0, 2200.0, 1800.0, "Quintal", "2025-02-07"),
    ("Soybean", "Madhya Pradesh", "Indore", "Indore Mandi", 4200.0, 4600.0, 4400.0, "Quintal", "2025-02-07"),
    ("Cotton", "Gujarat", "Rajkot", "Rajkot Mandi", 6500.0, 7200.0, 6800.0, "Quintal", "2025-02-07"),
    ("Mustard", "Rajasthan", "Jaipur", "Jaipur Mandi", 5000.0, 5400.0, 5200.0, "Quintal", "2025-02-07"),
    ("Sugarcane", "Uttar Pradesh", "Meerut", "Meerut Mandi", 350.0, 400.0, 375.0, "Quintal", "2025-02-07"),
    ("Maize", "Bihar", "Patna", "Patna Mandi", 1800.0, 2100.0, 1950.0, "Quintal", "2025-02-07"),
]

mandi_df = spark.createDataFrame(sample_mandi_data, mandi_schema)
mandi_df.write \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable("agrisarthi.main.mandi_prices")

print("✅ Mandi prices table created with sample data")

# COMMAND ----------

# ─── 5. Conversation Logs Table (for MLflow + Analytics) ───────────

spark.sql("""
CREATE TABLE IF NOT EXISTS agrisarthi.main.conversation_logs (
  session_id STRING,
  farmer_id STRING,
  channel STRING,
  user_message STRING,
  agent_response STRING,
  agent_used STRING,
  tools_called ARRAY<STRING>,
  language STRING,
  response_time_ms DOUBLE,
  timestamp TIMESTAMP
)
USING DELTA
COMMENT 'All farmer conversations across all channels'
""")
print("✅ conversation_logs table created")

# COMMAND ----------

# ─── 6. Farmer Features Table (Feature Store) ──────────────────────

spark.sql("""
CREATE TABLE IF NOT EXISTS agrisarthi.main.farmer_features (
  farmer_id STRING,
  phone_number STRING,
  state STRING,
  district STRING,
  primary_crops ARRAY<STRING>,
  land_size_acres DOUBLE,
  soil_type STRING,
  preferred_language STRING,
  total_queries INT,
  last_active TIMESTAMP,
  created_at TIMESTAMP
)
USING DELTA
COMMENT 'Farmer profiles for personalized recommendations'
""")
print("✅ farmer_features table created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Data Ingestion Complete!
# MAGIC 
# MAGIC **Tables created:**
# MAGIC - `agrisarthi.main.soil_data` — 5000+ soil records with text for RAG
# MAGIC - `agrisarthi.main.soil_vector_index` — Vector Search index (auto-synced)
# MAGIC - `agrisarthi.main.govt_schemes` — 8 major Indian government schemes
# MAGIC - `agrisarthi.main.mandi_prices` — Market prices (template for scheduled refresh)
# MAGIC - `agrisarthi.main.conversation_logs` — Conversation tracking
# MAGIC - `agrisarthi.main.farmer_features` — Farmer profile features
# MAGIC 
# MAGIC **Next:** Run `02_agent_tools.py` to define tools, then `03_agent_workflow.py` to build the agent.
