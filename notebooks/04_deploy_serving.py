"""
AgriSarthi v2 — Deploy Agent via Mosaic AI Agent Framework
Run this notebook AFTER notebook 03 has registered the agent in Unity Catalog.

Databricks tech used: Agent Framework, Model Serving, MLflow, AI Gateway, Serverless Compute
"""

# COMMAND ----------

# MAGIC %md
# MAGIC # 🚀 AgriSarthi — Deploy Agent via Agent Framework
# MAGIC 
# MAGIC This notebook:
# MAGIC 1. Verifies the registered agent model in Unity Catalog
# MAGIC 2. Deploys it via `databricks.agents.deploy()` (shows in Agent Bricks)
# MAGIC 3. Tests the endpoint with sample requests
# MAGIC 
# MAGIC **Prerequisite:** Notebook 03 must have been run first to register the model.

# COMMAND ----------

# MAGIC %pip install databricks-agents databricks-sdk mlflow --upgrade --quiet
# MAGIC %restart_python

# COMMAND ----------

# ─── 1. Verify Registered Model in Unity Catalog ────────────────────

import mlflow
from mlflow import MlflowClient

mlflow.set_registry_uri("databricks-uc")
model_name = "agrisarthi.main.agrisarthi_agent"

client = MlflowClient(registry_uri="databricks-uc")
versions = client.search_model_versions(f"name='{model_name}'")
if not versions:
    raise Exception(f"No model versions found for {model_name}. Run notebook 03 first!")

latest_version = max(int(v.version) for v in versions)
print(f"✅ Found model: {model_name} version {latest_version}")

# COMMAND ----------

# ─── 2. Deploy via Agent Framework ──────────────────────────────────
# Using databricks.agents.deploy() to register in Agent Bricks

from databricks import agents
import time

endpoint_name = "agrisarthi-agent"

print(f"🚀 Deploying {model_name} v{latest_version} via Agent Framework...")
print(f"   Endpoint name: {endpoint_name}")

try:
    deployment = agents.deploy(
        model_name=model_name,
        model_version=latest_version,
        environment_vars={
            "OPENWEATHERMAP_API_KEY": "{{secrets/agrisarthi/openweathermap-key}}",
            "DATABRICKS_HOST": "{{secrets/agrisarthi/databricks-host}}",
            "DATABRICKS_TOKEN": "{{secrets/agrisarthi/databricks-token}}",
            "DATABRICKS_SQL_WAREHOUSE_ID": "{{secrets/agrisarthi/sql-warehouse-id}}",
        },
    )
    print(f"✅ Agent deployment initiated!")
    print(f"   Endpoint: {deployment.endpoint_name}")
    print(f"   Query endpoint: {deployment.query_endpoint}")
except Exception as e:
    if "already exists" in str(e).lower() or "ALREADY_EXISTS" in str(e):
        print(f"⚠️ Endpoint already exists, updating with new version...")
        # Delete and recreate
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient()
            w.serving_endpoints.delete(endpoint_name)
            print(f"   Deleted old endpoint. Re-deploying...")
            time.sleep(5)
            deployment = agents.deploy(
                model_name=model_name,
                model_version=latest_version,
                environment_vars={
                    "OPENWEATHERMAP_API_KEY": "{{secrets/agrisarthi/openweathermap-key}}",
                    "DATABRICKS_HOST": "{{secrets/agrisarthi/databricks-host}}",
                    "DATABRICKS_TOKEN": "{{secrets/agrisarthi/databricks-token}}",
                    "DATABRICKS_SQL_WAREHOUSE_ID": "{{secrets/agrisarthi/sql-warehouse-id}}",
                },
            )
            print(f"✅ Agent re-deployed!")
            print(f"   Endpoint: {deployment.endpoint_name}")
        except Exception as e2:
            print(f"❌ Re-deploy failed: {e2}")
            raise
    else:
        print(f"❌ Deployment error: {e}")
        raise

# COMMAND ----------

# ─── 3. Wait for endpoint to be ready ───────────────────────────────

from databricks.sdk import WorkspaceClient
import time

w = WorkspaceClient()

print("⏳ Waiting for agent endpoint to become ready (can take 5-15 min)...")
max_wait = 900  # 15 minutes
start_time = time.time()

try:
    while time.time() - start_time < max_wait:
        try:
            ep = w.serving_endpoints.get(endpoint_name)
            state = ep.state
            elapsed = int(time.time() - start_time)
            ready = getattr(state, 'ready', None)
            config_update = getattr(state, 'config_update', None)
            
            if str(ready) == "READY":
                print(f"✅ Agent endpoint is READY! (took {elapsed}s)")
                print(f"   URL: {w.config.host}/serving-endpoints/{endpoint_name}/invocations")
                break
            else:
                print(f"   [{elapsed:>4d}s] Ready: {ready} | Config: {config_update}")
                time.sleep(30)
        except Exception as inner_e:
            elapsed = int(time.time() - start_time)
            print(f"   [{elapsed:>4d}s] Endpoint not yet available: {inner_e}")
            time.sleep(30)
    else:
        print(f"⚠️ Endpoint not ready after {max_wait}s. It may still be deploying.")
        print("   Check: Databricks UI → Serving → agrisarthi-agent")
except Exception as e:
    print(f"⚠️ Error during wait: {e}")
    print("   Check manually: Databricks UI → Serving / Agents")

# COMMAND ----------

# ─── 4. Test the Deployed Agent Endpoint ─────────────────────────────

import requests
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

try:
    endpoint_url = f"{w.config.host}/serving-endpoints/{endpoint_name}/invocations"
    headers = {
        "Authorization": f"Bearer {w.config.token}",
        "Content-Type": "application/json"
    }

    test_queries = [
        "What crops should I grow in Lucknow?",
        "What is the price of rice in Amritsar?",
        "Tell me about PM-KISAN scheme",
    ]

    for query in test_queries:
        payload = {"messages": [{"role": "user", "content": query}]}
        response = requests.post(endpoint_url, json=payload, headers=headers, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            # Agent framework may return different formats
            if "messages" in result:
                answer = result["messages"][-1].get("content", "No response")
            elif "output" in result:
                answer = str(result["output"])
            else:
                answer = str(result)[:300]
            print(f"✅ Q: {query}")
            print(f"   A: {answer[:200]}...")
            print()
        else:
            print(f"❌ Q: {query}")
            print(f"   Error: {response.status_code} — {response.text[:200]}")
            print()
except Exception as e:
    print(f"⚠️ Endpoint test skipped: {e}")
    print("   The agent may still be starting up. Test from the Serving UI or AI Playground.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Agent Deployed via Agent Framework!
# MAGIC 
# MAGIC **Visible in:** AI/ML → **Agents** (Agent Bricks)
# MAGIC 
# MAGIC **Endpoint:** `agrisarthi-agent`
# MAGIC 
# MAGIC **Features enabled:**
# MAGIC - Auto-captured inference logs in `agrisarthi.main`
# MAGIC - MLflow traces for every conversation
# MAGIC - AI Playground integration for testing
# MAGIC - Review App for human feedback
# MAGIC 
# MAGIC **Next:** Run `05_dashboard.py` for AI/BI analytics dashboard.
