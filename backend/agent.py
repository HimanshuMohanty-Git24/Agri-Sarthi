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
        user_input = messages[-1].content
        
        prompt = f"""
        You are the supervisor of a team of expert AI agents for Indian agriculture.
        Based on the user's query, determine which agent is best suited to handle it.

        Your available agents are:
        - SoilCropAdvisor: For questions about soil health, suitable crops for a location, fertilizers, and farming techniques.
        - MarketAnalyst: For questions about current market prices (mandi rates), price trends, and best places to sell produce.
        - FinancialAdvisor: For questions about government schemes, subsidies, loans, and financial planning for farmers.

        User Query: "{user_input}"

        Based on this query, respond with ONLY the name of the best agent to delegate the task to.
        If the query is a greeting or a general question, respond with "end".
        """
        
        response = llm.invoke(prompt)
        next_agent_name = response.content.strip()
        
        # Validate and default to 'end' if the response is not a valid agent name
        valid_agents = ["SoilCropAdvisor", "MarketAnalyst", "FinancialAdvisor"]
        if next_agent_name not in valid_agents:
            next_agent_name = "end"
        
        # Return a new state dict with the next_agent set
        return {"next_agent": next_agent_name}
        
    except Exception as e:
        print(f"Error in supervisor_agent: {e}")
        return {"next_agent": "end"}

def create_specialist_agent_node(agent_name: str, system_prompt: str):
    """
    A factory function to create a node for a specialist agent.
    This reduces code duplication.
    """
    def agent_node(state: AgentState):
        # print(f"---{agent_name.upper()}---")  # Remove debug output
        
        # Enhanced system prompt to ensure agent doesn't say its name
        enhanced_prompt = f"""{system_prompt}

ABSOLUTE CRITICAL RULE: 
- DO NOT SAY THE WORD "MarketAnalyst" OR ANY AGENT NAME AT ALL
- START IMMEDIATELY WITH YOUR ANSWER
- NO ROLE IDENTIFICATION WHATSOEVER

Example: If asked about potato price, respond EXACTLY like this:
"Based on current market data, potato in Lucknow is trading at ₹1220 per quintal (₹12.2 per kg)."

DO NOT start with agent names or role identification.
"""
        
        # Prepend the system prompt to the message history for this agent's turn
        messages_with_prompt = [HumanMessage(content=enhanced_prompt)] + state['messages']
        
        # Call the LLM with tools
        response = llm_with_tools.invoke(messages_with_prompt)
        
        # Simple post-processing to remove only explicit agent names
        if hasattr(response, 'content') and response.content:
            import re
            filtered_content = response.content
            
            # Only remove if the content starts with an agent name
            agent_names = ['MarketAnalyst', 'SoilCropAdvisor', 'FinancialAdvisor', 'Supervisor']
            for name in agent_names:
                # Only remove if it starts with the agent name followed by colon or space
                if filtered_content.strip().startswith(name):
                    filtered_content = re.sub(f'^{re.escape(name)}[:\s]*', '', filtered_content).strip()
                    break
            
            # Update the response content
            response.content = filtered_content
        
        # The agent's response is the final message in the list
        return {"messages": [response]}
        
    return agent_node

# Define the system prompts for each specialist agent
soil_crop_prompt = """
You are a professional agricultural advisor specializing in soil health and crop recommendations.

INSTRUCTIONS:
- Use the `soil_data_retriever` tool to get specific soil information for the farmer's location
- Use the `weather_alert_tool` if weather information is requested
- Provide clear, actionable advice that farmers can implement
- Be professional, helpful, and practical in your recommendations

RESPONSE FORMAT:
Structure your response with:
1. Brief soil analysis summary
2. Recommended crops for the soil type
3. Practical farming advice
4. Seasonal considerations (if applicable)

Do NOT include your role name in the response. Speak directly to the farmer as their trusted agricultural advisor.
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
You are a professional financial advisor specializing in agricultural finance and government schemes.

INSTRUCTIONS:
- Use the `tavily_search` or `duckduckgo_search` tools to find current information on government schemes, subsidies, and loans
- Provide clear, actionable guidance that farmers can understand and implement
- Focus on practical steps for accessing financial resources
- Include eligibility criteria and application processes

RESPONSE FORMAT:
Structure your response with:
1. Brief overview of available schemes/options
2. Eligibility requirements
3. How to apply (step-by-step)
4. Required documents
5. Contact information or helpful resources

Do NOT include your role name in the response. Speak directly to the farmer as their trusted financial advisor.
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
    Simple router - just ends conversation after agent response
    """
    try:
        last_message = state["messages"][-1]
        
        # If the last message is a tool call, route to tools
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        
        # Otherwise end the conversation
        return "end"
        
    except Exception as e:
        print(f"ERROR in main_router: {e}")
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
