"""
AgriSarthi v2 — AI/BI Dashboard + Genie Setup
Run this notebook in Databricks to create analytics views and dashboard queries.

Databricks tech used: AI/BI Dashboards, Genie, Delta Lake, Unity Catalog
"""

# COMMAND ----------

# MAGIC %md
# MAGIC # 📊 AgriSarthi — AI/BI Dashboard & Genie Analytics
# MAGIC 
# MAGIC This notebook creates SQL views and queries for:
# MAGIC 1. **AI/BI Dashboards** — Visual analytics on farmer usage
# MAGIC 2. **Genie** — Natural language analytics ("How many farmers asked about weather this week?")

# COMMAND ----------

# ─── Set catalog/schema context ──────────────────────────────────────

spark.sql("USE CATALOG agrisarthi")
spark.sql("USE SCHEMA main")
print("✅ Using agrisarthi.main")

# COMMAND ----------

# ─── Create analytics views (wrapped in try/except since tables may not exist yet) ──

views_sql = [
    # View 1: Daily Query Volume
    """CREATE OR REPLACE VIEW agrisarthi.main.v_daily_queries AS
SELECT 
  DATE(timestamp) as query_date,
  channel,
  COUNT(*) as total_queries,
  COUNT(DISTINCT farmer_id) as unique_farmers,
  AVG(response_time_ms) as avg_response_time_ms,
  PERCENTILE(response_time_ms, 0.95) as p95_response_time_ms
FROM agrisarthi.main.conversation_logs
GROUP BY DATE(timestamp), channel
ORDER BY query_date DESC""",

    # View 2: Agent Distribution
    """CREATE OR REPLACE VIEW agrisarthi.main.v_agent_distribution AS
SELECT 
  agent_used,
  COUNT(*) as query_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage,
  AVG(response_time_ms) as avg_response_time_ms
FROM agrisarthi.main.conversation_logs
GROUP BY agent_used
ORDER BY query_count DESC""",

    # View 3: Tool Usage Analytics
    """CREATE OR REPLACE VIEW agrisarthi.main.v_tool_usage AS
SELECT 
  tool_name,
  COUNT(*) as call_count,
  DATE(timestamp) as call_date
FROM agrisarthi.main.conversation_logs
LATERAL VIEW EXPLODE(tools_called) t AS tool_name
GROUP BY tool_name, DATE(timestamp)
ORDER BY call_date DESC, call_count DESC""",

    # View 4: Language Distribution
    """CREATE OR REPLACE VIEW agrisarthi.main.v_language_distribution AS
SELECT 
  language,
  channel,
  COUNT(*) as query_count,
  COUNT(DISTINCT farmer_id) as unique_farmers
FROM agrisarthi.main.conversation_logs
GROUP BY language, channel
ORDER BY query_count DESC""",

    # View 5: Top Queries by Crop
    """CREATE OR REPLACE VIEW agrisarthi.main.v_crop_interest AS
SELECT 
  crop_mentioned,
  COUNT(*) as mention_count,
  DATE(timestamp) as query_date
FROM (
  SELECT 
    timestamp,
    CASE
      WHEN LOWER(user_message) LIKE '%wheat%' THEN 'Wheat'
      WHEN LOWER(user_message) LIKE '%rice%' THEN 'Rice'
      WHEN LOWER(user_message) LIKE '%potato%' THEN 'Potato'
      WHEN LOWER(user_message) LIKE '%tomato%' THEN 'Tomato'
      WHEN LOWER(user_message) LIKE '%onion%' THEN 'Onion'
      WHEN LOWER(user_message) LIKE '%cotton%' THEN 'Cotton'
      WHEN LOWER(user_message) LIKE '%soybean%' THEN 'Soybean'
      WHEN LOWER(user_message) LIKE '%sugarcane%' THEN 'Sugarcane'
      WHEN LOWER(user_message) LIKE '%maize%' THEN 'Maize'
      WHEN LOWER(user_message) LIKE '%mustard%' THEN 'Mustard'
      ELSE 'Other'
    END as crop_mentioned
  FROM agrisarthi.main.conversation_logs
) subq
WHERE crop_mentioned != 'Other'
GROUP BY crop_mentioned, DATE(timestamp)
ORDER BY query_date DESC, mention_count DESC""",

    # View 6: State-wise Farmer Engagement
    """CREATE OR REPLACE VIEW agrisarthi.main.v_state_engagement AS
SELECT 
  f.state,
  COUNT(DISTINCT f.farmer_id) as total_farmers,
  SUM(f.total_queries) as total_queries,
  AVG(f.total_queries) as avg_queries_per_farmer,
  COLLECT_SET(f.primary_crops) as popular_crops
FROM agrisarthi.main.farmer_features f
GROUP BY f.state
ORDER BY total_farmers DESC""",

    # View 7: Scheme Interest Tracker
    """CREATE OR REPLACE VIEW agrisarthi.main.v_scheme_interest AS
SELECT 
  scheme_mentioned,
  COUNT(*) as mention_count
FROM (
  SELECT 
    CASE
      WHEN LOWER(user_message) LIKE '%pm-kisan%' OR LOWER(user_message) LIKE '%pm kisan%' THEN 'PM-KISAN'
      WHEN LOWER(user_message) LIKE '%kusum%' THEN 'PM-KUSUM'
      WHEN LOWER(user_message) LIKE '%pmfby%' OR LOWER(user_message) LIKE '%fasal bima%' THEN 'PMFBY'
      WHEN LOWER(user_message) LIKE '%kcc%' OR LOWER(user_message) LIKE '%kisan credit%' THEN 'KCC'
      WHEN LOWER(user_message) LIKE '%enam%' THEN 'eNAM'
      WHEN LOWER(user_message) LIKE '%soil health%' THEN 'Soil Health Card'
      ELSE 'Other Scheme'
    END as scheme_mentioned
  FROM agrisarthi.main.conversation_logs
  WHERE agent_used = 'FinancialAdvisor'
) subq
WHERE scheme_mentioned != 'Other Scheme'
GROUP BY scheme_mentioned
ORDER BY mention_count DESC""",
]

view_names = [
    "v_daily_queries", "v_agent_distribution", "v_tool_usage",
    "v_language_distribution", "v_crop_interest", "v_state_engagement",
    "v_scheme_interest",
]

for name, sql in zip(view_names, views_sql):
    try:
        spark.sql(sql)
        print(f"✅ Created view: {name}")
    except Exception as e:
        print(f"⚠️ View {name} skipped (table may not exist yet): {str(e)[:100]}")

print(f"\n🎉 Dashboard views setup complete!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🧪 Genie Sample Questions
# MAGIC 
# MAGIC These are natural language questions that **Genie** can answer using the views above:
# MAGIC 
# MAGIC 1. "How many farmers used the system today?"
# MAGIC 2. "Which agent gets the most queries?"
# MAGIC 3. "What is the average response time for weather queries?"
# MAGIC 4. "Which crops are farmers asking about the most?"
# MAGIC 5. "How many queries came from WhatsApp vs Web?"
# MAGIC 6. "Which state has the most active farmers?"
# MAGIC 7. "What government scheme is most popular?"
# MAGIC 8. "Show me the daily trend of total queries this week"
# MAGIC 9. "Which language do most farmers prefer?"
# MAGIC 10. "How has the P95 response time changed over the last 7 days?"
# MAGIC 
# MAGIC ### Setting up Genie:
# MAGIC 1. Go to **SQL Warehouses** → Create a Serverless SQL Warehouse
# MAGIC 2. Go to **Genie** → New Genie Space
# MAGIC 3. Add tables: `agrisarthi.main.conversation_logs`, `agrisarthi.main.farmer_features`
# MAGIC 4. Add all views created above
# MAGIC 5. Genie can now answer natural language questions about farmer usage!

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📊 AI/BI Dashboard Layout
# MAGIC 
# MAGIC Create a new **AI/BI Dashboard** with these panels:
# MAGIC 
# MAGIC | Panel | Query Source | Chart Type |
# MAGIC |---|---|---|
# MAGIC | Daily Active Farmers | `v_daily_queries` | Line chart |
# MAGIC | Query Volume by Channel | `v_daily_queries` | Stacked bar |
# MAGIC | Agent Distribution | `v_agent_distribution` | Pie chart |
# MAGIC | Tool Usage Heatmap | `v_tool_usage` | Heatmap |
# MAGIC | Language Distribution | `v_language_distribution` | Donut chart |
# MAGIC | Top Crops | `v_crop_interest` | Bar chart |
# MAGIC | State Engagement Map | `v_state_engagement` | Choropleth map |
# MAGIC | Scheme Interest | `v_scheme_interest` | Horizontal bar |
# MAGIC | P95 Response Time | `v_daily_queries` | Line chart |
# MAGIC | Live Query Feed | `conversation_logs` | Table (last 10) |

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Analytics Complete!
# MAGIC 
# MAGIC **Created:**
# MAGIC - 7 analytics views for dashboards
# MAGIC - Genie space configuration guide
# MAGIC - AI/BI Dashboard layout specification
# MAGIC 
# MAGIC **Databricks Tech Used:**
# MAGIC - AI/BI Dashboards for visual analytics
# MAGIC - Genie for natural language data queries
# MAGIC - Delta Lake for all underlying data
# MAGIC - Unity Catalog for governance
