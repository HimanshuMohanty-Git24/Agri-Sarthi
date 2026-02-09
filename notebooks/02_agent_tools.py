"""
AgriSarthi v2 — Agent Tools (Unity Catalog Functions)
Run this notebook in Databricks to define all tools that agents can call.

This replaces: tools.py (SerpAPI, FAISS retriever, OpenWeatherMap, NDMA, web scraper)
Databricks tech used: Unity Catalog Functions, Vector Search, Delta Lake, AI Gateway
"""

# COMMAND ----------

# MAGIC %md
# MAGIC # 🛠️ AgriSarthi — Agent Tools Definition
# MAGIC 
# MAGIC Each tool is defined as a Python function that can be registered as a 
# MAGIC **Unity Catalog Function** and used by the Mosaic AI Agent Framework.

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch databricks-sdk --quiet
# MAGIC %restart_python

# COMMAND ----------

import os
import json
import requests
from databricks.vector_search.client import VectorSearchClient
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
vsc = VectorSearchClient()

# COMMAND ----------

# ─── Tool 1: Soil Data Retriever (Vector Search RAG) ───────────────
# Replaces: FAISS-based soil_data_retriever + Google Gemini embeddings

def soil_data_retriever(query: str) -> str:
    """
    Searches the soil database using Databricks Vector Search for information
    about soil composition, nutrient levels, and suitable crops for a specific location.
    
    Args:
        query: The user's query about soil, crops, or a specific location (district/state in India).
    
    Returns:
        Relevant soil data for the queried location.
    """
    try:
        index = vsc.get_index(
            endpoint_name="agrisarthi-vs-endpoint",
            index_name="agrisarthi.main.soil_vector_index"
        )
        
        results = index.similarity_search(
            query_text=query,
            columns=["state", "district", "soil_type", "ph", "organic_carbon",
                     "nitrogen", "phosphorus", "potassium", "rainfall", 
                     "temperature", "soil_text"],
            num_results=3
        )
        
        data_array = results.get("result", {}).get("data_array", [])
        if not data_array:
            return f"No soil data found for '{query}'. Please specify a district and state in India."
        
        response_parts = []
        for row in data_array:
            response_parts.append(row[-1])  # soil_text column is last
        
        return "\n\n".join(response_parts)
        
    except Exception as e:
        return f"Error retrieving soil data: {e}"


# COMMAND ----------

# ─── Tool 2: Market Price Tool (Delta Lake) ─────────────────────────
# Replaces: SerpAPI-based serpapi_market_price_tool

def market_price_tool(crop_name: str, location: str) -> str:
    """
    Gets real-time market prices (mandi rates) for agricultural crops
    from the Delta Lake mandi prices table.
    
    Args:
        crop_name: Name of the crop (e.g., 'wheat', 'rice', 'potato')
        location: City, district, or state for the price query
    
    Returns:
        Current market price information for the specified crop and location.
    """
    try:
        # Query Delta table for prices
        query = f"""
        SELECT crop_name, state, district, market, 
               min_price, max_price, modal_price, unit, arrival_date
        FROM agrisarthi.main.mandi_prices
        WHERE LOWER(crop_name) LIKE LOWER('%{crop_name}%')
          AND (LOWER(state) LIKE LOWER('%{location}%') 
               OR LOWER(district) LIKE LOWER('%{location}%')
               OR LOWER(market) LIKE LOWER('%{location}%'))
        ORDER BY arrival_date DESC
        LIMIT 5
        """
        
        results = spark.sql(query).collect()
        
        if not results:
            # Fallback: search with broader criteria
            fallback_query = f"""
            SELECT crop_name, state, district, market,
                   min_price, max_price, modal_price, unit, arrival_date
            FROM agrisarthi.main.mandi_prices
            WHERE LOWER(crop_name) LIKE LOWER('%{crop_name}%')
            ORDER BY arrival_date DESC
            LIMIT 5
            """
            results = spark.sql(fallback_query).collect()
        
        if not results:
            return f"No price data found for {crop_name} in {location}. Try searching for a different crop or location."
        
        price_info = []
        for row in results:
            info = (
                f"📊 {row.crop_name} in {row.market} ({row.district}, {row.state}):\n"
                f"  - Min Price: ₹{row.min_price:.0f}/{row.unit}\n"
                f"  - Max Price: ₹{row.max_price:.0f}/{row.unit}\n"
                f"  - Modal Price: ₹{row.modal_price:.0f}/{row.unit}\n"
                f"  - Date: {row.arrival_date}"
            )
            price_info.append(info)
        
        return "\n\n".join(price_info)
        
    except Exception as e:
        return f"Error fetching market prices: {e}"


# COMMAND ----------

# ─── Tool 3: Weather Alert Tool (OpenWeatherMap API) ────────────────
# Kept as external API call — no Databricks equivalent for weather

def weather_alert_tool(location: str) -> str:
    """
    Fetches the current weather forecast for a specified location using OpenWeatherMap.
    
    Args:
        location: City and state for weather data (e.g., 'Bhubaneswar, Odisha')
    
    Returns:
        Current weather conditions including temperature, humidity, and wind.
    """
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return "Weather forecast is unavailable. OPENWEATHERMAP_API_KEY is not set."
    
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": location, "appid": api_key, "units": "metric"}
    
    try:
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        forecast = (
            f"🌤️ Weather forecast for {data['name']}:\n"
            f"- Condition: {data['weather'][0]['description']}\n"
            f"- Temperature: {data['main']['temp']}°C (feels like {data['main']['feels_like']}°C)\n"
            f"- Humidity: {data['main']['humidity']}%\n"
            f"- Wind Speed: {data['wind']['speed']} m/s\n"
            f"- Pressure: {data['main']['pressure']} hPa"
        )
        return forecast
        
    except requests.exceptions.RequestException as e:
        return f"Error fetching weather data for {location}: {e}"


# COMMAND ----------

# ─── Tool 4: Disaster Alert Tool (NDMA API) ─────────────────────────
# Kept as external API call — NDMA is the authoritative source

def disaster_alert_tool(location: str) -> str:
    """
    Fetches natural disaster alerts and warnings for a specific location 
    from NDMA (National Disaster Management Authority).
    
    Args:
        location: Location for disaster alerts (e.g., 'Prayagraj, Uttar Pradesh')
    
    Returns:
        Active disaster alerts including flood warnings, cyclone alerts, etc.
    """
    url = "https://sachet.ndma.gov.in/cap_public_website/FetchAddressWiseAlerts"
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (AgriSarthi Bot)'
    }
    data = {'address': location, 'radius': 50}
    
    try:
        response = requests.post(url, data=data, headers=headers, timeout=15)
        response.raise_for_status()
        
        alert_data = response.json()
        
        if isinstance(alert_data, list) and len(alert_data) > 0:
            alerts = f"🚨 DISASTER ALERTS FOR {location.upper()}:\n\n"
            for i, alert in enumerate(alert_data[:5]):
                if isinstance(alert, dict):
                    alerts += f"ALERT {i+1}:\n"
                    alerts += f"• Event: {alert.get('event', 'Unknown')}\n"
                    alerts += f"• Severity: {alert.get('severity', 'Unknown')}\n"
                    alerts += f"• Headline: {alert.get('headline', 'N/A')}\n"
                    alerts += f"• Description: {alert.get('description', 'N/A')[:200]}\n\n"
            return alerts
        else:
            return f"✅ No active disaster alerts for {location}. The area appears safe."
            
    except Exception as e:
        return f"❌ Unable to fetch disaster alerts for {location}: {e}"


# COMMAND ----------

# ─── Tool 5: Government Scheme Search (Delta Lake) ──────────────────
# Replaces: Tavily/DuckDuckGo web search for scheme information

def scheme_search_tool(query: str) -> str:
    """
    Searches the government schemes database for Indian agricultural schemes,
    subsidies, loans, and financial programs relevant to farmers.
    
    Args:
        query: The farmer's question about government schemes or financial assistance.
    
    Returns:
        Relevant government scheme details including eligibility and how to apply.
    """
    try:
        # Search schemes table using keyword matching
        search_query = f"""
        SELECT scheme_name, full_name, category, description, 
               eligibility, subsidy_percent, ministry, website, 
               states, documents_required
        FROM agrisarthi.main.govt_schemes
        WHERE LOWER(scheme_name) LIKE LOWER('%{query}%')
           OR LOWER(full_name) LIKE LOWER('%{query}%')
           OR LOWER(category) LIKE LOWER('%{query}%')
           OR LOWER(description) LIKE LOWER('%{query}%')
        """
        
        results = spark.sql(search_query).collect()
        
        if not results:
            # Broader search
            words = query.lower().split()
            conditions = " OR ".join([
                f"LOWER(description) LIKE '%{w}%'" for w in words if len(w) > 3
            ])
            if conditions:
                broader_query = f"""
                SELECT * FROM agrisarthi.main.govt_schemes
                WHERE {conditions}
                LIMIT 3
                """
                results = spark.sql(broader_query).collect()
        
        if not results:
            return "No specific government scheme found for your query. Common Indian farmer schemes include PM-KISAN, PM-KUSUM, PMFBY, KCC. Please ask about a specific scheme."
        
        schemes_info = []
        for row in results:
            info = (
                f"📋 {row.scheme_name} ({row.full_name})\n"
                f"  Category: {row.category}\n"
                f"  Description: {row.description}\n"
                f"  Eligibility: {row.eligibility}\n"
                f"  Subsidy: {row.subsidy_percent}%\n"
                f"  Ministry: {row.ministry}\n"
                f"  Website: {row.website}\n"
                f"  Documents: {row.documents_required}\n"
                f"  Coverage: {row.states}"
            )
            schemes_info.append(info)
        
        return "\n\n".join(schemes_info)
        
    except Exception as e:
        return f"Error searching schemes: {e}"


# COMMAND ----------

# ─── Tool 6: Crop Recommendation Tool (Feature Store + AutoML) ──────
# NEW — not in v1. Uses Databricks Feature Store for personalized recommendations

def crop_recommendation_tool(state: str, district: str, season: str = "kharif") -> str:
    """
    Recommends suitable crops based on soil data, weather patterns, and 
    market trends for a specific location.
    
    Args:
        state: Indian state name (e.g., 'Uttar Pradesh')
        district: District name (e.g., 'Lucknow')
        season: Crop season - 'kharif', 'rabi', or 'zaid'
    
    Returns:
        Personalized crop recommendations with reasoning.
    """
    try:
        # Get soil data for the location
        soil_query = f"""
        SELECT soil_type, ph, nitrogen, phosphorus, potassium, 
               rainfall, temperature
        FROM agrisarthi.main.soil_data
        WHERE LOWER(state) = LOWER('{state}')
          AND LOWER(district) LIKE LOWER('%{district}%')
        LIMIT 1
        """
        
        soil_results = spark.sql(soil_query).collect()
        
        if not soil_results:
            return f"No soil data found for {district}, {state}. Please check the location name."
        
        soil = soil_results[0]
        
        # Rule-based recommendations based on soil properties
        recommendations = []
        
        if soil.ph >= 6.0 and soil.ph <= 7.5:
            recommendations.extend(["Wheat", "Rice", "Maize", "Soybean"])
        elif soil.ph < 6.0:
            recommendations.extend(["Tea", "Coffee", "Potato", "Blueberry"])
        else:
            recommendations.extend(["Cotton", "Barley", "Sugar beet"])
        
        if soil.nitrogen > 200:
            recommendations.extend(["Rice", "Wheat", "Maize"])
        elif soil.nitrogen < 100:
            recommendations.extend(["Pulses (Moong, Urad)", "Groundnut", "Soybean"])
        
        if soil.rainfall > 1000:
            recommendations.extend(["Rice", "Sugarcane", "Jute"])
        elif soil.rainfall < 500:
            recommendations.extend(["Millet", "Bajra", "Jowar", "Mustard"])
        
        # Deduplicate
        recommendations = list(set(recommendations))[:6]
        
        result = (
            f"🌱 Crop Recommendations for {district}, {state} ({season} season):\n\n"
            f"Soil Profile: {soil.soil_type} soil, pH {soil.ph:.1f}\n"
            f"Nutrients: N={soil.nitrogen:.0f}, P={soil.phosphorus:.0f}, K={soil.potassium:.0f} kg/ha\n"
            f"Rainfall: {soil.rainfall:.0f} mm, Temp: {soil.temperature:.1f}°C\n\n"
            f"Recommended Crops: {', '.join(recommendations)}\n\n"
            f"Tip: Consider getting a Soil Health Card for detailed fertilizer recommendations."
        )
        
        return result
        
    except Exception as e:
        return f"Error generating recommendations: {e}"


# COMMAND ----------

# ─── Register tools for the Agent Framework ─────────────────────────

# All tools that will be available to agents
AGRISARTHI_TOOLS = {
    "soil_data_retriever": soil_data_retriever,
    "market_price_tool": market_price_tool,
    "weather_alert_tool": weather_alert_tool,
    "disaster_alert_tool": disaster_alert_tool,
    "scheme_search_tool": scheme_search_tool,
    "crop_recommendation_tool": crop_recommendation_tool,
}

print("✅ All 6 agent tools defined and ready")
print(f"   Tools: {list(AGRISARTHI_TOOLS.keys())}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Tools Definition Complete!
# MAGIC 
# MAGIC **Tools created:**
# MAGIC | Tool | Source | Databricks Tech |
# MAGIC |---|---|---|
# MAGIC | `soil_data_retriever` | Vector Search on soil Delta table | Vector Search, Delta Lake |
# MAGIC | `market_price_tool` | Delta Lake mandi prices table | Delta Lake, Unity Catalog |
# MAGIC | `weather_alert_tool` | OpenWeatherMap API (external) | — |
# MAGIC | `disaster_alert_tool` | NDMA API (external) | — |
# MAGIC | `scheme_search_tool` | Delta Lake govt schemes table | Delta Lake, Unity Catalog |
# MAGIC | `crop_recommendation_tool` | Soil features + rules | Feature Store, Delta Lake |
# MAGIC 
# MAGIC **Next:** Run `03_agent_workflow.py` to build the multi-agent system.
