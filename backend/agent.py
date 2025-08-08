import os
from typing import Annotated, List, Literal
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from tools import all_tools

print("🤖 Starting agent initialization...")

# --- Agent State ---
# This defines the "memory" or state of our graph. Each node will modify this state.
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    # This field will be used to route the flow to the correct agent
    next_agent: Literal["Supervisor", "SoilCropAdvisor", "MarketAnalyst", "FinancialAdvisor", "end"]

# --- LLM and Tool Setup ---
# Initialize the fast Groq LLM
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    print("ERROR: GROQ_API_KEY not found in environment variables!")
    print("Please add your Groq API key to the .env file.")
    raise ValueError("GROQ_API_KEY is required but not found")

llm = ChatGroq(temperature=0, model_name="llama3-8b-8192", api_key=groq_api_key)
print("✅ Groq LLM initialized successfully")

# Bind the tools to the LLM so it knows how to call them
print("🔗 Binding tools to LLM...")
llm_with_tools = llm.bind_tools(all_tools)
print("✅ Tools bound to LLM successfully")

# The ToolNode will execute the tools when called by an agent
print("🛠️  Creating ToolNode...")
tool_node = ToolNode(all_tools)
print("✅ ToolNode created successfully")

# --- Agent Definitions ---

def supervisor_agent(state: AgentState):
    """
    The Supervisor is the main entry point and router. It decides which specialist agent
    should handle the user's query based on its content.
    """
    try:
        messages = state['messages']
        user_input = messages[-1].content.lower()
        
        print(f"🎯 Supervisor analyzing query: {user_input}")
        
        # Weather and disaster alert keywords
        weather_keywords = ['weather', 'temperature', 'rain', 'forecast', 'climate', 'humidity', 'wind']
        disaster_keywords = ['flood', 'warning', 'alert', 'disaster', 'cyclone', 'storm', 'drought', 'heatwave']
        soil_keywords = ['soil', 'crop', 'fertilizer', 'farming', 'cultivation', 'nutrients']
        price_keywords = ['price', 'rate', 'mandi', 'market', 'sell', 'cost']
        finance_keywords = ['loan', 'scheme', 'subsidy', 'financial', 'bank', 'government']
        
        # Check for weather/disaster related queries first
        if any(keyword in user_input for keyword in weather_keywords + disaster_keywords):
            print("🌤️ Routing to SoilCropAdvisor for weather/disaster query")
            return {"next_agent": "SoilCropAdvisor"}
        
        # Check for market price queries
        elif any(keyword in user_input for keyword in price_keywords):
            print("💰 Routing to MarketAnalyst for price query")
            return {"next_agent": "MarketAnalyst"}
        
        # Check for financial queries
        elif any(keyword in user_input for keyword in finance_keywords):
            print("🏦 Routing to FinancialAdvisor for financial query")
            return {"next_agent": "FinancialAdvisor"}
        
        # Check for soil/crop queries
        elif any(keyword in user_input for keyword in soil_keywords):
            print("🌱 Routing to SoilCropAdvisor for soil/crop query")
            return {"next_agent": "SoilCropAdvisor"}
        
        # Use LLM as fallback for complex queries
        else:
            prompt = f"""
            You are the supervisor of a team of expert AI agents for Indian agriculture.
            Based on the user's query, determine which agent is best suited to handle it.

            Your available agents are:
            - SoilCropAdvisor: For questions about soil health, suitable crops for a location, fertilizers, farming techniques, WEATHER, and DISASTER ALERTS
            - MarketAnalyst: For questions about current market prices (mandi rates), price trends, and best places to sell produce
            - FinancialAdvisor: For questions about government schemes, subsidies, loans, and financial planning for farmers

            User Query: "{user_input}"

            Based on this query, respond with ONLY the name of the best agent to delegate the task to.
            If the query is a greeting or a general question, respond with "end".
            """
            
            response = llm.invoke(prompt)
            next_agent_name = response.content.strip()
            
            print(f"🤖 LLM suggested agent: {next_agent_name}")
            
            # Validate and default to 'end' if the response is not a valid agent name
            valid_agents = ["SoilCropAdvisor", "MarketAnalyst", "FinancialAdvisor"]
            if next_agent_name not in valid_agents:
                next_agent_name = "end"
            
            return {"next_agent": next_agent_name}
        
    except Exception as e:
        print(f"❌ Error in supervisor_agent: {e}")
        return {"next_agent": "end"}

def create_specialist_agent_node(agent_name: str, system_prompt: str):
    """
    A factory function to create a node for a specialist agent.
    This reduces code duplication.
    """
    def agent_node(state: AgentState):
        print(f"🔄 {agent_name} is processing the query...")
        
        # Get the original user query to analyze
        user_query = ""
        for msg in state['messages']:
            if hasattr(msg, 'content') and isinstance(msg.content, str) and not msg.content.startswith("You are"):
                user_query = msg.content
                break
        
        print(f"🔍 Analyzing user query: {user_query}")
        
        # Check if this is a FinancialAdvisor handling Indian schemes
        if agent_name == "FinancialAdvisor":
            # Make query India-specific
            enhanced_prompt = f"""{system_prompt}

CRITICAL: You are helping an Indian farmer. Search specifically for Indian government schemes.

User Query: "{user_query}"

When searching, use terms like:
- "India farmer electricity subsidy scheme"
- "Indian government PM-KUSUM scheme" 
- "India agriculture electricity scheme"
- "Indian farmer solar pump scheme"
- "Government of India electricity subsidy farmers"

Focus ONLY on Indian schemes - PM-KUSUM, state electricity subsidies, solar schemes, etc.
"""
        
        # Check if this is a SoilCropAdvisor handling weather/disaster queries
        elif agent_name == "SoilCropAdvisor":
            query_lower = user_query.lower()
            needs_weather = any(word in query_lower for word in ['weather', 'temperature', 'climate', 'forecast'])
            needs_disaster = any(word in query_lower for word in ['flood', 'warning', 'alert', 'disaster', 'rain warning', 'flooding', 'waring'])
            
            # Check what tools have already been called
            called_tools = set()
            for msg in state["messages"]:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        called_tools.add(tool_call.get('name', ''))
            
            print(f"🌤️ Needs weather: {needs_weather}, Needs disaster alerts: {needs_disaster}")
            print(f"🛠️ Already called tools: {called_tools}")
            
            if needs_weather and needs_disaster:
                # For combined queries, force explicit tool usage
                if 'weather_alert_tool' not in called_tools and 'disaster_alert_tool' not in called_tools:
                    # Neither tool called yet - prioritize calling both
                    enhanced_prompt = f"""{system_prompt}

CRITICAL INSTRUCTIONS: This query requires BOTH weather and disaster information.
User Query: "{user_query}"

You MUST call weather_alert_tool first for the location mentioned in the query.
Do NOT provide a final answer yet - just call the weather tool.
"""
                elif 'weather_alert_tool' in called_tools and 'disaster_alert_tool' not in called_tools:
                    # Weather tool called, now need disaster tool
                    enhanced_prompt = f"""{system_prompt}

CRITICAL: You have weather data but the user also asked about flooding/rain warnings/alerts.
User Query: "{user_query}"

You MUST now call disaster_alert_tool for the same location to get disaster alerts.
Do NOT provide a final answer yet - call the disaster alert tool.
"""
                elif 'disaster_alert_tool' in called_tools and 'weather_alert_tool' not in called_tools:
                    # Disaster tool called, now need weather tool
                    enhanced_prompt = f"""{system_prompt}

CRITICAL: You have disaster alert data but the user also asked about weather.
User Query: "{user_query}"

You MUST now call weather_alert_tool for the same location to get weather information.
Do NOT provide a final answer yet - call the weather tool.
"""
                else:
                    # Both tools have been called, now provide comprehensive answer
                    enhanced_prompt = f"""{system_prompt}

You now have both weather and disaster alert data. Provide a comprehensive response combining both results.
"""
            elif needs_disaster and 'disaster_alert_tool' not in called_tools:
                # Only disaster query
                enhanced_prompt = f"""{system_prompt}

CRITICAL: The user is asking about disaster alerts/warnings/flooding. You MUST use disaster_alert_tool.
User Query: "{user_query}"

Call disaster_alert_tool for the location mentioned in the query.
"""
            elif needs_weather and 'weather_alert_tool' not in called_tools:
                # Only weather query
                enhanced_prompt = f"""{system_prompt}

CRITICAL: The user is asking about weather. You MUST use weather_alert_tool.
User Query: "{user_query}"

Call weather_alert_tool for the location mentioned in the query.
"""
            else:
                enhanced_prompt = system_prompt
        else:
            enhanced_prompt = system_prompt
        
        # Add the critical rule about not mentioning agent names
        enhanced_prompt += """

ABSOLUTE CRITICAL RULE: 
- DO NOT SAY ANY AGENT NAME, ROLE NAME, OR IDENTIFIER
- DO NOT say "WeatherAgent", "MarketAnalyst", "SoilCropAdvisor", "FinancialAdvisor", or "Supervisor"
- START IMMEDIATELY WITH YOUR ANSWER
- NO ROLE IDENTIFICATION WHATSOEVER

Example: If asked about weather, respond EXACTLY like this:
"The current weather in Prayagraj shows..."

DO NOT start with agent names or role identification.
"""
        
        # Prepend the system prompt to the message history for this agent's turn
        messages_with_prompt = [HumanMessage(content=enhanced_prompt)] + state['messages']
        
        print(f"📨 Sending query to LLM for {agent_name}...")
        
        # Call the LLM with tools
        response = llm_with_tools.invoke(messages_with_prompt)
        
        print(f"✅ {agent_name} received response from LLM")
        
        # Log tool calls if any
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"🔧 {agent_name} is calling tools: {[call.get('name', 'unknown') for call in response.tool_calls]}")
        
        # Enhanced post-processing to remove any role identifiers
        if hasattr(response, 'content') and response.content:
            import re
            filtered_content = response.content
            
            # Remove any agent or role names that might appear
            unwanted_names = [
                'MarketAnalyst', 'SoilCropAdvisor', 'FinancialAdvisor', 'Supervisor',
                'WeatherAgent', 'Weather Agent', 'Disaster Agent', 'DisasterAgent'
            ]
            
            for name in unwanted_names:
                # Remove if it starts with the name
                if filtered_content.strip().startswith(name):
                    filtered_content = re.sub(f'^{re.escape(name)}[:\s]*', '', filtered_content).strip()
                # Also remove if it appears anywhere in the text with common patterns
                filtered_content = re.sub(f'{re.escape(name)}[:\s]*', '', filtered_content)
            
            # Clean up any remaining artifacts
            filtered_content = re.sub(r'^\W+', '', filtered_content)  # Remove leading non-word chars
            
            # Ensure it starts with a capital letter
            if filtered_content and not filtered_content[0].isupper():
                filtered_content = filtered_content[0].upper() + filtered_content[1:] if len(filtered_content) > 1 else filtered_content.upper()
            
            # Update the response content
            response.content = filtered_content
            
            print(f"🧹 {agent_name} cleaned response: {filtered_content[:100]}...")
        
        # The agent's response is the final message in the list
        return {"messages": [response]}
        
    return agent_node

# Define the system prompts for each specialist agent
soil_crop_prompt = """
You are a professional agricultural advisor specializing in soil health, crop recommendations, weather information, and disaster alerts.

CRITICAL TOOL USAGE INSTRUCTIONS:

For queries that mention BOTH weather AND disaster alerts/warnings/flooding:
You MUST call BOTH tools in sequence:
1. weather_alert_tool(location="User's Location")
2. disaster_alert_tool(location="User's Location")

For queries that mention only weather (temperature, forecast, climate):
- Use only weather_alert_tool(location="User's Location")

For queries that mention only disaster alerts (flooding, warnings, alerts, rain warnings):
- Use only disaster_alert_tool(location="User's Location")

For soil/crop queries:
- Use soil_data_retriever(query="User's query")

IMPORTANT: If the user asks "What is the weather in [Location] and is there any flooding or rain warning?", you MUST use BOTH tools.

After getting tool results, provide a comprehensive response combining all the information.

Always start your response directly with the information - DO NOT mention agent names or roles.
"""

market_analyst_prompt = """
You provide market information to farmers.

CRITICAL: DO NOT mention any role names or agent identifiers.

Use serpapi_market_price_tool for price queries.

Always respond exactly like this example:
"Based on current market data, potato in Lucknow is trading at ₹1220 per quintal (₹12.2 per kg). This represents the latest mandi prices for today."

Start directly with "Based on current market data" - no other text before it.
"""

financial_advisor_prompt = """
You are a professional financial advisor specializing in agricultural finance and government schemes in INDIA.

CRITICAL INSTRUCTIONS:
- You MUST focus ONLY on Indian government schemes, subsidies, and programs
- Always search for "India" or "Indian government" specific schemes
- Do NOT provide information about US, European, or other international programs
- Focus on central and state government initiatives in India

SEARCH STRATEGY:
- You are a India Centric financial advisor so Only focus on Indian central & state government schemes
- Use terms like "India farmer electricity subsidy", "PM-KUSUM scheme", "Indian agriculture electricity scheme"
- Look for schemes from Ministry of Agriculture, Ministry of Power, Government of India
- Include state-specific schemes for farmers

RESPONSE FORMAT:
Structure your response with:
1. Brief overview of available Indian schemes/options
2. Eligibility requirements (for Indian farmers)
3. How to apply (Indian government procedures)
4. Required documents (Indian documents like Aadhaar, land records)
5. Contact information (Indian government offices/websites)

IMPORTANT INDIAN SCHEMES TO MENTION:
- PM-KUSUM (Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyan)
- State electricity subsidies for farmers
- Solar pump schemes
- Agricultural connection schemes

Do NOT include your role name in the response. Speak directly to the Indian farmer as their trusted advisor.
"""

# Create the agent nodes using the factory function
soil_crop_agent = create_specialist_agent_node("SoilCropAdvisor", soil_crop_prompt)
market_analyst_agent = create_specialist_agent_node("MarketAnalyst", market_analyst_prompt)
financial_advisor_agent = create_specialist_agent_node("FinancialAdvisor", financial_advisor_prompt)

# --- Graph Definition ---

# Define the routing logic after a tool has been called
def after_tool_call_router(state: AgentState):
    """
    After a tool is called, we want to route back to the agent that called it
    so it can process the tool's output.
    """
    last_message = state["messages"][-2] # The AI message that called the tool
    # The tool call information is in the 'tool_calls' attribute
    if last_message.tool_calls:
        # We can route based on which agent's prompt generated this tool call,
        # but for simplicity, we'll just go back to the supervisor to re-evaluate.
        # A more complex router could track the "calling agent".
        return "Supervisor"
    return "end"

# Simple main router for agents after they complete
def main_router(state: AgentState):
    """
    Enhanced router that handles multi-tool scenarios
    """
    try:
        last_message = state["messages"][-1]
        
        # If the last message is a tool call, route to tools
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            print(f"🔧 Routing to tools. Tool calls: {[call.get('name', 'unknown') for call in last_message.tool_calls]}")
            return "tools"
        
        # Check if this was a SoilCropAdvisor response that might need additional tool calls
        if len(state["messages"]) >= 2:
            previous_message = state["messages"][-2]
            if hasattr(previous_message, 'tool_calls') and previous_message.tool_calls:
                # Get the original user query
                original_query = ""
                for msg in reversed(state["messages"]):
                    if hasattr(msg, 'content') and isinstance(msg.content, str) and not msg.content.startswith("You are"):
                        original_query = msg.content.lower()
                        break
                
                print(f"🔍 Checking if additional tools needed for: {original_query}")
                
                # Check if we need both weather and disaster tools
                needs_weather = any(word in original_query for word in ['weather', 'temperature', 'climate', 'forecast'])
                needs_disaster = any(word in original_query for word in ['flood', 'warning', 'alert', 'disaster', 'rain warning', 'flooding'])
                
                # Check what tools were already called
                called_tools = set()
                for msg in state["messages"]:
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            called_tools.add(tool_call.get('name', ''))
                
                print(f"🛠️ Tools already called: {called_tools}")
                print(f"🌤️ Needs weather: {needs_weather}, Needs disaster: {needs_disaster}")
                
                # If we need both tools but only called one, continue processing
                if needs_weather and needs_disaster:
                    if 'weather_alert_tool' in called_tools and 'disaster_alert_tool' not in called_tools:
                        print("⚠️ Need to call disaster_alert_tool, routing back to Supervisor")
                        return "Supervisor"
                    elif 'disaster_alert_tool' in called_tools and 'weather_alert_tool' not in called_tools:
                        print("⚠️ Need to call weather_alert_tool, routing back to Supervisor")
                        return "Supervisor"
        
        # Otherwise end the conversation
        print("🏁 Ending conversation")
        return "end"
        
    except Exception as e:
        print(f"❌ ERROR in main_router: {e}")
        return "end"

# Create the StateGraph
workflow = StateGraph(AgentState)

# Add the nodes to the graph
workflow.add_node("Supervisor", supervisor_agent)
workflow.add_node("SoilCropAdvisor", soil_crop_agent)
workflow.add_node("MarketAnalyst", market_analyst_agent)
workflow.add_node("FinancialAdvisor", financial_advisor_agent)
workflow.add_node("tools", tool_node)

# Define the edges (the flow of the conversation)
workflow.set_entry_point("Supervisor")

# Create a safe routing function for the Supervisor
def supervisor_router(state: AgentState):
    """Safe routing function that handles KeyError"""
    try:
        next_agent = state.get("next_agent", "end")
        
        # Ensure we return a valid route
        valid_routes = ["SoilCropAdvisor", "MarketAnalyst", "FinancialAdvisor", "end"]
        if next_agent in valid_routes:
            return next_agent
        else:
            return "end"
    except Exception as e:
        print(f"ERROR in supervisor_router: {e}")
        return "end"

workflow.add_conditional_edges(
    "Supervisor",
    supervisor_router,
    {
        "SoilCropAdvisor": "SoilCropAdvisor",
        "MarketAnalyst": "MarketAnalyst", 
        "FinancialAdvisor": "FinancialAdvisor",
        "end": END
    }
)
workflow.add_conditional_edges(
    "SoilCropAdvisor",
    main_router,
    {"tools": "tools", "end": END}
)
workflow.add_conditional_edges(
    "MarketAnalyst",
    main_router,
    {"tools": "tools", "end": END}
)
workflow.add_conditional_edges(
    "FinancialAdvisor",
    main_router,
    {"tools": "tools", "end": END}
)
workflow.add_edge("tools", "Supervisor") # After any tool call, go back to supervisor to decide next step

# Compile the graph into a runnable app
print("🔄 Compiling agentic workflow...")
agentic_workflow = workflow.compile()

print("🎉 Agentic workflow compiled successfully!")
