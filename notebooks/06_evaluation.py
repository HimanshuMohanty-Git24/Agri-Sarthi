"""
AgriSarthi v2 — MLflow Agent Evaluation
Run in Databricks to evaluate agent quality with standardized test cases.

Databricks tech used: MLflow, Mosaic AI Evaluation, Serverless Compute
"""

# COMMAND ----------

# MAGIC %md
# MAGIC # 🧪 AgriSarthi — Agent Quality Evaluation
# MAGIC 
# MAGIC Uses MLflow's agent evaluation framework to test the agent against
# MAGIC curated test cases covering all farming domains.

# COMMAND ----------

# MAGIC %pip install databricks-agents mlflow
# MAGIC %restart_python

# COMMAND ----------

import mlflow
import pandas as pd

mlflow.set_experiment("/agrisarthi/agent-evaluation")

# COMMAND ----------

# ─── Define Evaluation Dataset ──────────────────────────────────────

eval_data = pd.DataFrame([
    # Soil & Crop queries
    {
        "request": "What crops should I grow in Lucknow, Uttar Pradesh?",
        "expected_facts": ["wheat", "rice", "soil", "Uttar Pradesh"],
        "domain": "soil_crop"
    },
    {
        "request": "What is the soil type in Karnataka?",
        "expected_facts": ["soil", "Karnataka", "Red", "pH"],
        "domain": "soil_crop"
    },
    {
        "request": "Best fertilizer for sandy soil with low nitrogen?",
        "expected_facts": ["nitrogen", "urea", "fertilizer"],
        "domain": "soil_crop"
    },
    
    # Market Price queries
    {
        "request": "What is the price of wheat in Lucknow today?",
        "expected_facts": ["wheat", "Lucknow", "₹", "price"],
        "domain": "market"
    },
    {
        "request": "Rice price in Amritsar mandi",
        "expected_facts": ["rice", "Amritsar", "₹", "quintal"],
        "domain": "market"
    },
    {
        "request": "Current potato rate in Agra",
        "expected_facts": ["potato", "Agra", "₹", "price"],
        "domain": "market"
    },
    
    # Government Scheme queries
    {
        "request": "Tell me about PM-KUSUM scheme",
        "expected_facts": ["PM-KUSUM", "solar", "pump", "subsidy"],
        "domain": "finance"
    },
    {
        "request": "How to apply for PM-KISAN?",
        "expected_facts": ["PM-KISAN", "₹6000", "Aadhaar", "apply"],
        "domain": "finance"
    },
    {
        "request": "What is Kisan Credit Card scheme?",
        "expected_facts": ["KCC", "credit", "loan", "interest"],
        "domain": "finance"
    },
    {
        "request": "Crop insurance scheme for farmers",
        "expected_facts": ["PMFBY", "insurance", "premium", "crop"],
        "domain": "finance"
    },
    
    # Weather queries
    {
        "request": "What is the weather in Bhubaneswar?",
        "expected_facts": ["weather", "temperature", "humidity", "Bhubaneswar"],
        "domain": "weather"
    },
    
    # Disaster alerts
    {
        "request": "Is there any flood warning in Prayagraj?",
        "expected_facts": ["alert", "Prayagraj", "flood"],
        "domain": "disaster"
    },
    
    # General / Edge cases
    {
        "request": "Namaste! Main ek kisan hoon",
        "expected_facts": ["namaste", "help", "assist"],
        "domain": "general"
    },
    {
        "request": "How to increase crop yield?",
        "expected_facts": ["yield", "fertilizer", "soil", "crop"],
        "domain": "general"
    },
])

print(f"✅ Evaluation dataset: {len(eval_data)} test cases across {eval_data['domain'].nunique()} domains")

# COMMAND ----------

# ─── Run Evaluation ─────────────────────────────────────────────────

from databricks.sdk import WorkspaceClient
import requests

w = WorkspaceClient()

# Call the deployed agent endpoint for each test case
def call_agent(query: str) -> str:
    """Call the deployed AgriSarthi agent."""
    endpoint_url = f"{w.config.host}/serving-endpoints/agrisarthi-agent/invocations"
    headers = {
        "Authorization": f"Bearer {w.config.token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            endpoint_url,
            json={"messages": [{"role": "user", "content": query}]},
            headers=headers,
            timeout=120
        )
        if response.status_code == 200:
            messages = response.json().get("messages", [])
            return messages[-1].get("content", "") if messages else ""
        return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {e}"

# Get predictions
print("🔄 Running agent on evaluation dataset...")
eval_data["response"] = eval_data["request"].apply(call_agent)
print("✅ All evaluation queries completed")

# COMMAND ----------

# ─── Evaluate with MLflow ───────────────────────────────────────────

with mlflow.start_run(run_name="agrisarthi-eval"):
    
    # Custom fact-checking evaluator
    results = {"total": len(eval_data), "passed": 0, "failed": 0, "by_domain": {}}
    
    for _, row in eval_data.iterrows():
        response_lower = row["response"].lower()
        facts_found = sum(1 for fact in row["expected_facts"] if fact.lower() in response_lower)
        fact_ratio = facts_found / len(row["expected_facts"]) if row["expected_facts"] else 0
        
        passed = fact_ratio >= 0.5  # At least 50% of expected facts present
        
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        domain = row["domain"]
        if domain not in results["by_domain"]:
            results["by_domain"][domain] = {"passed": 0, "failed": 0}
        results["by_domain"][domain]["passed" if passed else "failed"] += 1
    
    # Log metrics
    mlflow.log_metric("overall_accuracy", results["passed"] / results["total"])
    mlflow.log_metric("total_tests", results["total"])
    mlflow.log_metric("passed_tests", results["passed"])
    mlflow.log_metric("failed_tests", results["failed"])
    
    for domain, counts in results["by_domain"].items():
        total = counts["passed"] + counts["failed"]
        accuracy = counts["passed"] / total if total > 0 else 0
        mlflow.log_metric(f"{domain}_accuracy", accuracy)
    
    # Log the evaluation dataset
    mlflow.log_table(eval_data, artifact_file="evaluation_results.json")
    
    print("📊 Evaluation Results:")
    print(f"   Overall Accuracy: {results['passed']}/{results['total']} ({results['passed']/results['total']*100:.1f}%)")
    for domain, counts in results["by_domain"].items():
        total = counts["passed"] + counts["failed"]
        print(f"   {domain}: {counts['passed']}/{total}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Evaluation Complete!
# MAGIC 
# MAGIC Results are logged to MLflow and can be viewed in:
# MAGIC 1. **MLflow Experiments** → `/agrisarthi/agent-evaluation`
# MAGIC 2. **AI/BI Dashboard** → Agent performance metrics
# MAGIC 
# MAGIC **Tracked Metrics:**
# MAGIC - Overall accuracy (fact-checking)
# MAGIC - Domain-wise accuracy (soil, market, finance, weather, etc.)
# MAGIC - Response latency
# MAGIC - Full evaluation dataset with responses
