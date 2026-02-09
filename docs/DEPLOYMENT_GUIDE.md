# AgriSarthi v2 — Hackathon Deployment Guide (Step-by-Step)

> **Workspace URL:** https://dbc-54e28175-826c.cloud.databricks.com  
> **Estimated Time:** ~45 minutes end-to-end  
> **Prerequisites:** Databricks workspace access, a Personal Access Token (PAT), API keys for OpenWeatherMap + Sarvam AI

---

## Phase 0: Prerequisites Setup (10 min)

### 0.1 — Generate a Databricks Personal Access Token (PAT)

1. Go to https://dbc-54e28175-826c.cloud.databricks.com
2. Click your **profile icon** (top-right) → **Settings**
3. Go to **Developer** → **Access Tokens** → **Generate New Token**
4. Name: `agrisarthi-hackathon`, Lifetime: `90 days`
5. **Copy the token immediately** — you won't see it again!

### 0.2 — Install Databricks CLI locally

```powershell
pip install databricks-cli databricks-sdk
```

Configure it:
```powershell
databricks configure --token
# Host: https://dbc-54e28175-826c.cloud.databricks.com
# Token: <paste your PAT>
```

Verify:
```powershell
databricks workspace list /
```
You should see your home folder listed.

### 0.3 — Set up Secret Scope for API Keys

```powershell
# Create a scope (old CLI uses --scope flag)
databricks secrets create-scope --scope agrisarthi

# Store your API keys (old CLI uses --scope/--key/--string-value)
databricks secrets put --scope agrisarthi --key openweathermap-key --string-value "YOUR_OPENWEATHERMAP_KEY"
databricks secrets put --scope agrisarthi --key sarvam-api-key --string-value "YOUR_SARVAM_API_KEY"
databricks secrets put --scope agrisarthi --key datagov-api-key --string-value "YOUR_DATAGOV_KEY"

# Verify secrets
databricks secrets list --scope agrisarthi
```

Or run the helper script (set env vars first):
```powershell
$env:OPENWEATHERMAP_API_KEY = "your_key"
$env:SARVAM_API_KEY = "your_key"
python Agri-Sarthi/databricks/setup_secrets.py
```

---

## Phase 1: Upload Data & Run Data Ingestion (Step 1)

### 1.1 — Create Unity Catalog Volume for Raw Data

1. Open the Databricks workspace: https://dbc-54e28175-826c.cloud.databricks.com
2. In left sidebar, click **SQL Editor**
3. Run these SQL commands one by one:

```sql
CREATE CATALOG IF NOT EXISTS agrisarthi;
USE CATALOG agrisarthi;
CREATE SCHEMA IF NOT EXISTS main;
USE SCHEMA main;
CREATE VOLUME IF NOT EXISTS raw;
```

### 1.2 — Upload soildata.csv to the Volume

**Option A — Databricks UI (easiest):**
1. Left sidebar → **Catalog** → Navigate to: `agrisarthi` → `main` → `Volumes` → `raw`
2. Click **Upload to this volume**
3. Select `Agri-Sarthi/backend/soildata.csv` from your local machine
4. Wait for upload to complete

**Option B — Databricks CLI:**
```powershell
databricks fs cp "Agri-Sarthi/backend/soildata.csv" "dbfs:/Volumes/agrisarthi/main/raw/soildata.csv"
```

**Option C — DBFS (fallback if Volumes aren't available):**
```powershell
databricks fs cp "Agri-Sarthi/backend/soildata.csv" "dbfs:/FileStore/agrisarthi/soildata.csv"
```
> If using DBFS, you'll need to edit `01_data_ingestion.py` line 47:
> Change `soil_csv_path = "/Volumes/agrisarthi/main/raw/soildata.csv"` 
> to `soil_csv_path = "dbfs:/FileStore/agrisarthi/soildata.csv"`

### 1.3 — Import and Run 01_data_ingestion.py

1. Left sidebar → **Workspace** → Navigate to your user folder (`/Users/your-email/`)
2. Click **⋮** → **Import**
3. Upload: `Agri-Sarthi/databricks/notebooks/01_data_ingestion.py`
4. It will open as a Databricks notebook (cells separated by `# COMMAND ----------`)
5. Click **Connect** (top-right) → select a cluster:
   - **Best option:** Use an existing **Serverless** cluster (free tier)
   - **Alternative:** Create a new cluster → Single Node, `Standard_DS3_v2`, auto-terminate 30 min
6. **Run All** (top menu) or press `Ctrl+Shift+Enter`

**Expected Output per cell:**
| Cell | Expected Output |
|------|----------------|
| 1 (SQL) | "OK" — catalog & schema created |
| 2 (Load CSV) | `✅ Loaded 5001 soil records` + schema printout |
| 3 (Add text + write) | `✅ Soil data saved to Delta table` |
| 4 (SQL verify) | Table showing 5 soil records |
| 5 (VS endpoint) | `✅ Vector Search endpoint created` (or "already exists") |
| 6 (VS index) | `✅ Vector Search index created` |
| 7 (VS test) | 3 search results with district, state, soil type |
| 8 (Schemes) | `✅ 8 government schemes loaded` |
| 9 (Mandi prices) | `✅ Mandi prices table created` |
| 10 (Conv logs SQL) | "OK" — table created |
| 11 (Features SQL) | "OK" — table created |

> **⚠️ Vector Search Note:** The index creation takes **5-10 minutes** to complete. The cell will return immediately, but the index syncs in the background. You can check status in: left sidebar → **Compute** → **Vector Search endpoints** → `agrisarthi-vs-endpoint`.

### 1.4 — Verify Data Ingestion

In the **SQL Editor**, run:
```sql
-- Check all tables were created
SHOW TABLES IN agrisarthi.main;

-- Verify row counts
SELECT 'soil_data' as tbl, COUNT(*) FROM agrisarthi.main.soil_data
UNION ALL
SELECT 'govt_schemes', COUNT(*) FROM agrisarthi.main.govt_schemes
UNION ALL  
SELECT 'mandi_prices', COUNT(*) FROM agrisarthi.main.mandi_prices;
```

Expected: soil_data ~5001 rows, govt_schemes 8 rows, mandi_prices 10 rows.

---

## Phase 2: Define Agent Tools (Step 2)

### 2.1 — Import and Run 02_agent_tools.py

1. **Workspace** → **Import** → Upload `02_agent_tools.py`
2. **Connect** same cluster as Step 1
3. **Run All**

This notebook defines 6 tool functions:
- `soil_data_retriever` — Vector Search lookup
- `market_price_tool` — Delta table SQL query
- `weather_alert_tool` — OpenWeatherMap API
- `disaster_alert_tool` — NDMA API
- `scheme_search_tool` — Delta table SQL query
- `crop_recommendation_tool` — Feature Store + rules

**Expected:** Each cell prints `✅ Tool defined: <name>` and the final cell runs a test query.

> **⚠️ If Vector Search index is still syncing**, the soil_data_retriever test may fail. Wait a few minutes and re-run just that test cell.

---

## Phase 3: Build the Agent (Step 3)

### 3.1 — Import and Run 03_agent_workflow.py

1. **Workspace** → **Import** → Upload `03_agent_workflow.py`
2. **Connect** same cluster
3. **Run All**

**What happens in each cell:**

| Cell | What It Does |
|------|-------------|
| 1 | Installs `databricks-agents mlflow langchain langgraph` + restarts Python kernel |
| 2 | Sets up MLflow experiment `/agrisarthi/agent-traces` |
| 3 | Creates `ChatDatabricks` LLM (Llama 3.1 70B via AI Gateway) |
| 4 | Imports tool functions from cell 2's definitions |
| 5 | Defines supervisor agent node |
| 6 | Defines 3 specialist agents (SoilCrop, Market, Finance) |
| 7 | Defines FinalAnswer agent |
| 8 | Builds LangGraph state machine and compiles it |
| 9 | **Test:** Sends "What crops grow best in sandy soil of Rajasthan?" and prints response |

> **⚠️ IMPORTANT:** Cell 1 will restart the Python kernel. After it restarts, the cluster detaches briefly. **Wait 10 seconds**, then click **Run All** again or run from Cell 2 onward.

> **⚠️ Cell 3 (ChatDatabricks) Note:** If you get `EndpointNotFound`, the foundation model endpoint isn't available. In that case:
> - Try: `endpoint="databricks-meta-llama-3-1-8b-instruct"` (smaller, always available)
> - Or go to **Serving** in the sidebar and check what foundation models are available

---

## Phase 4: Deploy to Model Serving (Step 4)

### 4.1 — Import and Run 04_deploy_serving.py

1. **Workspace** → **Import** → Upload `04_deploy_serving.py`
2. **Connect** same cluster
3. **Important:** Before running, check that notebook 03 variables are available. If not, add this cell at the top after pip install:

```python
%run ./03_agent_workflow
```

4. **Run All**

**What happens:**

| Cell | What It Does |
|------|-------------|
| 1 | Installs packages (may restart kernel) |
| 2 | Runs `%run ./03_agent_workflow` to load the compiled agent |
| 3 | Logs agent to MLflow under `agrisarthi.main.agrisarthi_agent` |
| 4 | Deploys as Model Serving endpoint `agrisarthi-agent` |
| 5 | Waits for endpoint to become ready, then runs a test query |

> **⚠️ Endpoint deployment takes 5-15 minutes.** The notebook will poll and wait. You can also check: left sidebar → **Serving** → look for `agrisarthi-agent`.

### 4.2 — Verify the Endpoint

Once deployed, test from the Databricks UI:
1. Left sidebar → **Serving**
2. Click **agrisarthi-agent**
3. Go to **Test** tab
4. Paste this test input:
```json
{
  "messages": [{"role": "user", "content": "What is the best crop for Lucknow in winter?"}]
}
```
5. Click **Send Request**
6. You should get an AI-generated farming recommendation!

**Or test via curl:**
```powershell
$headers = @{
    "Authorization" = "Bearer YOUR_DATABRICKS_PAT"
    "Content-Type" = "application/json"
}
$body = '{"messages": [{"role": "user", "content": "Best crop for sandy soil?"}]}'
Invoke-RestMethod -Uri "https://dbc-54e28175-826c.cloud.databricks.com/serving-endpoints/agrisarthi-agent/invocations" -Method POST -Headers $headers -Body $body
```

---

## Phase 5: Start the Local Gateway (Step 5)

### 5.1 — Create .env file

```powershell
cd d:\Accenture\Databricks_Hackthon\Agri-Sarthi
copy databricks\.env.example databricks\.env
```

Edit `databricks\.env` and fill in:
```dotenv
DATABRICKS_HOST=https://dbc-54e28175-826c.cloud.databricks.com
DATABRICKS_TOKEN=dapi_YOUR_ACTUAL_PAT_TOKEN
DATABRICKS_AGENT_ENDPOINT=agrisarthi-agent

# External APIs (copy from your original .env)
OPENWEATHERMAP_API_KEY=your_actual_key
SARVAM_API_KEY=your_actual_key
SARVAM_API_URL=https://api.sarvam.ai/v1
```

### 5.2 — Install Python dependencies

```powershell
cd d:\Accenture\Databricks_Hackthon\Agri-Sarthi
pip install -r databricks/requirements.txt
```

### 5.3 — Start the Gateway

```powershell
cd d:\Accenture\Databricks_Hackthon\Agri-Sarthi
uvicorn databricks.gateway:app --host 0.0.0.0 --port 8000 --reload
```

**Expected output:**
```
INFO:     Will watch for changes in these directories: [...]
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
🚀 AgriSarthi v2 Gateway started!
   Databricks endpoint: agrisarthi-agent
   Health check: http://localhost:8000/health
```

### 5.4 — Verify the Gateway

Open a new terminal:
```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Test chat
$body = '{"message": "What crops grow in Bihar?", "session_id": "test-123"}'
Invoke-RestMethod -Uri "http://localhost:8000/chat/sync" -Method POST -Body $body -ContentType "application/json"
```

---

## Phase 6: Launch the Frontend (Step 6)

### 6.1 — Install and Start React App

```powershell
cd d:\Accenture\Databricks_Hackthon\Agri-Sarthi\frontend
npm install
npm start
```

**Expected:** Browser opens at http://localhost:3000 with the AgriSarthi chat interface.

### 6.2 — Test End-to-End

1. Type a message in Hindi or English: `"मुझे लखनऊ में गेहूं की खेती के बारे में बताओ"`
2. The frontend → calls `localhost:8000/chat` → FastAPI gateway → calls Databricks Model Serving → agent runs on Databricks with Llama 3.1 → response streams back
3. You should see a detailed farming recommendation!

> **If the frontend's API URL is different**, check [frontend/src/services/sarvamService.js](frontend/src/services/sarvamService.js) or [frontend/src/components/Chat.js](frontend/src/components/Chat.js) and update the backend URL to `http://localhost:8000`.

---

## Phase 7: Set Up Analytics Dashboard (Step 7)

### 7.1 — Import and Run 05_dashboard.py

1. **Workspace** → **Import** → Upload `05_dashboard.py`
2. **Connect** cluster → **Run All**
3. This creates 7 SQL views for analytics

### 7.2 — Create AI/BI Dashboard

1. Left sidebar → **Dashboards** → **Create Dashboard**
2. Name: `AgriSarthi - Farmer Analytics`
3. Add widgets using these SQL queries:

**Widget 1 — Daily Query Volume:**
```sql
SELECT * FROM agrisarthi.main.v_daily_queries ORDER BY query_date DESC LIMIT 30;
```
Chart type: Line chart, X=query_date, Y=total_queries

**Widget 2 — Agent Distribution:**
```sql
SELECT * FROM agrisarthi.main.v_agent_distribution;
```
Chart type: Pie chart

**Widget 3 — Top Crops:**
```sql
SELECT * FROM agrisarthi.main.v_crop_interest LIMIT 10;
```
Chart type: Bar chart

**Widget 4 — State Engagement:**
```sql
SELECT * FROM agrisarthi.main.v_state_engagement LIMIT 15;
```
Chart type: Map or Bar chart

### 7.3 — Set Up Genie (AI-Powered Data Q&A)

1. Left sidebar → **Genie** → **New Genie Space**
2. Name: `AgriSarthi Insights`
3. Add tables: `agrisarthi.main.conversation_logs`, `agrisarthi.main.soil_data`, `agrisarthi.main.mandi_prices`
4. Now you can ask questions like:
   - "How many farmers asked about wheat this week?"
   - "What's the most common soil type queried?"
   - "Show me average mandi prices by state"

---

## Quick Reference — Command Cheat Sheet

```powershell
# ─── Full Deployment in Order ─────────────────────────────────────

# 0. Setup CLI
pip install databricks-cli databricks-sdk
databricks configure --token

# 1. Upload data
databricks fs cp "Agri-Sarthi/backend/soildata.csv" "dbfs:/Volumes/agrisarthi/main/raw/soildata.csv"

# 2-4. Run notebooks in Databricks UI (01 → 02 → 03 → 04)

# 5. Start gateway locally
cd d:\Accenture\Databricks_Hackthon\Agri-Sarthi
pip install -r databricks/requirements.txt
copy databricks\.env.example databricks\.env  # Edit with real values!
uvicorn databricks.gateway:app --host 0.0.0.0 --port 8000

# 6. Start frontend  
cd d:\Accenture\Databricks_Hackthon\Agri-Sarthi\frontend
npm install
npm start

# 7. Run 05_dashboard.py in Databricks, then create dashboard in UI
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `EndpointNotFound` for LLM | Go to **Serving** → check available foundation models. Try `databricks-meta-llama-3-1-8b-instruct` |
| Vector Search index stuck | Wait 10 min. Check Compute → Vector Search endpoints for status |
| `CATALOG_NOT_FOUND` | Run the SQL: `CREATE CATALOG IF NOT EXISTS agrisarthi; CREATE SCHEMA IF NOT EXISTS agrisarthi.main;` |
| `VOLUME_NOT_FOUND` | Create volume: `CREATE VOLUME IF NOT EXISTS agrisarthi.main.raw;` then re-upload CSV |
| Model Serving endpoint not ready | Takes 5-15 min. Check **Serving** tab → Status should be "Ready" |
| Gateway can't connect to Databricks | Check `.env` has correct `DATABRICKS_HOST` and `DATABRICKS_TOKEN` |
| Frontend shows 404/CORS error | Ensure gateway is running on port 8000. Check `REACT_APP_API_URL` in frontend |
| `%pip install` fails in notebook | Cluster might need internet access. Check network settings |
| Secrets scope error | Old CLI: `databricks secrets create-scope --scope agrisarthi` / New CLI: `databricks secrets create-scope agrisarthi` |
| `asyncpg` connection refused | Lakebase may not be set up. Gateway works without it — sessions stay in-memory |

---

## Architecture Flow (Runtime)

```
Farmer (Phone/Web/WhatsApp)
    │
    ▼
React Frontend (localhost:3000)  ───or───  WhatsApp (WPPConnect)
    │                                           │
    ▼                                           ▼
FastAPI Gateway (localhost:8000)  ◄──────  WP Main v2
    │
    ▼
Databricks Model Serving (/serving-endpoints/agrisarthi-agent/invocations)
    │
    ▼
LangGraph Agent (Supervisor → Specialists → FinalAnswer)
    │
    ├─→ Vector Search (soil data RAG)
    ├─→ Delta Tables (mandi prices, schemes)
    ├─→ OpenWeatherMap API (weather)
    ├─→ NDMA API (disasters)
    └─→ MLflow (trace logging)
```
