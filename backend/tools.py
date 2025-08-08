import os
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_community.utilities import SerpAPIWrapper
from rag import rag_system

# --- Tool Definitions ---

# 1. Advanced Search for General Research (Financial Schemes, etc.)
# Initialize with error handling for missing API key
print("🔄 Initializing search tools...")
try:
    from langchain_community.tools import TavilySearchResults
    tavily_tool = TavilySearchResults(max_results=5)
    print("✅ Tavily search tool initialized successfully")
except Exception as e:
    print(f"⚠️  Warning: Tavily search tool failed to initialize: {e}")
    tavily_tool = None

# 2. Fallback Search
try:
    from langchain_community.tools import DuckDuckGoSearchRun
    duckduckgo_tool = DuckDuckGoSearchRun()
    print("✅ DuckDuckGo search tool initialized successfully")
except Exception as e:
    print(f"⚠️  Warning: DuckDuckGo search tool failed to initialize: {e}")
    duckduckgo_tool = None

# 3. Specialized Market Price Search using SerpApi for accuracy
try:
    serpapi_search = SerpAPIWrapper(serpapi_api_key=os.getenv("SERPAPI_API_KEY"))
    print("✅ SerpAPI search tool initialized successfully")
except Exception as e:
    print(f"⚠️  Warning: SerpAPI search tool failed to initialize: {e}")
    serpapi_search = None

print("🛠️  All tools initialization completed")

class MarketPriceToolInput(BaseModel):
    crop_name: str = Field(description="The name of the agricultural crop, e.g., 'potato', 'tomato'.")
    location: str = Field(description="The city or mandi name for the price query, e.g., 'Lucknow'.")

@tool("serpapi_market_price_tool", args_schema=MarketPriceToolInput)
def serpapi_market_price_tool(crop_name: str, location: str) -> str:
    """
    Uses SerpApi to get accurate, real-time market prices (mandi rates) for a specific crop in a given location.
    This is the preferred tool for all price-related queries.
    """
    if not serpapi_search:
        return "SerpAPI is not available. Please set SERPAPI_API_KEY in your .env file."
    # print(f"--- Calling SerpApi for: {crop_name} in {location} ---")  # Remove debug output
    query = f"today's {crop_name} price in {location} mandi"
    return serpapi_search.run(query)

# 4. Soil Data Retrieval
class SoilToolInput(BaseModel):
    query: str = Field(description="The user's query about soil, crops, or a specific location like a district and state.")

@tool("soil_data_retriever", args_schema=SoilToolInput)
def soil_data_retriever(query: str) -> str:
    """
    Searches the soil database for information about soil composition, nutrient levels, and suitable crops for a specific location.
    """
    if not rag_system or not rag_system.retriever:
        return "Soil data system is not available. Please ensure the GOOGLE_API_KEY is set up correctly."
    try:
        docs = rag_system.retriever.invoke(query)
        if not docs:
            return f"No soil data found for a query related to '{query}'. Please specify a district and state in India."
        return "\n\n".join([doc.page_content for doc in docs])
    except Exception as e:
        return f"Error retrieving soil data: {e}"

# 5. Weather & Alert Data
class WeatherToolInput(BaseModel):
    location: str = Field(description="The city and state for which to get the weather forecast, e.g., 'Bhubaneswar, Odisha'.")

@tool("weather_alert_tool", args_schema=WeatherToolInput)
def weather_alert_tool(location: str) -> str:
    """
    Fetches the current weather forecast for a specified location.
    """
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return "Weather forecast is unavailable. OPENWEATHERMAP_API_KEY is not set."
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": location, "appid": api_key, "units": "metric"}
    try:
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        weather_data = response.json()
        forecast = (
            f"Weather forecast for {weather_data['name']}:\n"
            f"- Condition: {weather_data['weather'][0]['description']}\n"
            f"- Temperature: {weather_data['main']['temp']}°C (feels like {weather_data['main']['feels_like']}°C)\n"
            f"- Humidity: {weather_data['main']['humidity']}%\n"
            f"- Wind Speed: {weather_data['wind']['speed']} m/s\n"
        )
        return forecast
    except requests.exceptions.RequestException as e:
        return f"Error fetching weather data for {location}: {e}"

# 6. Natural Disaster Alert Tool
class DisasterAlertToolInput(BaseModel):
    location: str = Field(description="The location for which to fetch disaster alerts, e.g., 'Prayagraj, Uttar Pradesh'.")

@tool("disaster_alert_tool", args_schema=DisasterAlertToolInput)
def disaster_alert_tool(location: str) -> str:
    """
    Fetches natural disaster alerts and warnings for a specific location using NDMA (National Disaster Management Authority) data.
    This includes flood warnings, cyclone alerts, heat wave warnings, and other natural disaster information.
    """
    print(f"🚨 Fetching disaster alerts for: {location}")
    
    url = "https://sachet.ndma.gov.in/cap_public_website/FetchAddressWiseAlerts"
    
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    data = {
        'address': location,
        'radius': 50  # 50 km radius
    }
    
    try:
        print(f"📡 Making request to NDMA API for {location}...")
        response = requests.post(url, data=data, headers=headers, timeout=15)
        response.raise_for_status()
        
        try:
            alert_data = response.json()
            print(f"✅ Successfully received alert data for {location}")
            
            if isinstance(alert_data, list) and len(alert_data) > 0:
                alerts_summary = f"🚨 DISASTER ALERTS FOR {location.upper()}:\n\n"
                
                for i, alert in enumerate(alert_data[:5]):  # Limit to 5 most recent alerts
                    if isinstance(alert, dict):
                        event_type = alert.get('event', 'Unknown Event')
                        severity = alert.get('severity', 'Unknown')
                        headline = alert.get('headline', 'No headline available')
                        description = alert.get('description', 'No description available')
                        effective = alert.get('effective', 'Unknown time')
                        
                        alerts_summary += f"ALERT {i+1}:\n"
                        alerts_summary += f"• Event: {event_type}\n"
                        alerts_summary += f"• Severity: {severity}\n"
                        alerts_summary += f"• Headline: {headline}\n"
                        alerts_summary += f"• Description: {description[:200]}...\n"
                        alerts_summary += f"• Effective: {effective}\n\n"
                
                return alerts_summary
            else:
                return f"✅ No active disaster alerts found for {location}. The area appears to be safe from major natural disasters at this time."
                
        except Exception as json_error:
            # If JSON parsing fails, try to extract useful text
            response_text = response.text
            if "no alerts" in response_text.lower() or len(response_text.strip()) < 10:
                return f"✅ No active disaster alerts found for {location}. The area appears to be safe from major natural disasters at this time."
            else:
                return f"⚠️ Received response but couldn't parse alert data for {location}. Raw response: {response_text[:500]}"
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching disaster alerts for {location}: {e}")
        return f"❌ Unable to fetch disaster alerts for {location} due to network error: {str(e)}. Please try again later."
    except Exception as e:
        print(f"❌ Unexpected error in disaster_alert_tool: {e}")
        return f"❌ An unexpected error occurred while fetching disaster alerts: {str(e)}"

# 7. Web Scraper
class ScraperToolInput(BaseModel):
    url: str = Field(description="The URL of the webpage to scrape for information.")

@tool("web_scraper_tool", args_schema=ScraperToolInput)
def web_scraper_tool(url: str) -> str:
    """
    Scrapes the text content of a given URL.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        text = ' '.join(p.get_text() for p in soup.find_all('p'))
        if not text:
            text = soup.get_text(separator=' ', strip=True)
        return text[:4000]
    except Exception as e:
        return f"Error scraping URL {url}: {e}"

# List of all tools for the agents
all_tools = [serpapi_market_price_tool, soil_data_retriever, weather_alert_tool, disaster_alert_tool, web_scraper_tool]

# Add search tools only if they're available
if tavily_tool:
    all_tools.append(tavily_tool)
if duckduckgo_tool:
    all_tools.append(duckduckgo_tool)