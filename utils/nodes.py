import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Literal, Optional
from utils.state import GraphState
from utils.llm import Base_llm
from utils.tools import getMarketPrice, getCropLocations, disease_Detect, Wheat_disease_detection, Find_scheme, Scheme_detials, Weather_tool, FIXED_IMAGE_PATH
import os

# --- Helper for extraction ---
class MarketArgs(BaseModel):
    crop: str = Field(description="Name of the crop")
    location: str = Field(description="City or district name", default="")
    state_name: str = Field(description="State name", default="")

class WeatherArgs(BaseModel):
    location: str = Field(description="City or Indian city name")

class SchemeArgs(BaseModel):
    query_type: str = Field(description="Either 'list' to list schemes or 'details' to get details of a specific scheme")
    scheme_link: str = Field(description="Link of the scheme if query_type is 'details'", default="")

# Output model for Chat Node to decide next step
class ChatDecision(BaseModel):
    """Decide whether to answer directly or call a tool."""
    decision: Literal["respond", "call_market", "call_disease", "call_weather", "call_scheme"] = Field(
        ..., description="Action to take. 'respond' if you can answer, or 'call_X' if you need data."
    )
    final_response: Optional[str] = Field(description="The final response to the user if decision is 'respond'.")
    refined_query: Optional[str] = Field(description="The refined query to use for calling a tool, resolving pronouns or missing context from memory.")

# --- Nodes ---

def market_node(state: GraphState) -> GraphState:
    print("---MARKET NODE---")
    transcript = state["transcript"]
    
    # Extract args
    structured_llm = Base_llm.with_structured_output(MarketArgs)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract crop, location (district), and state from the user query. Default to empty string if not found."),
        ("human", "{question}")
    ])
    chain = prompt | structured_llm
    try:
        args = chain.invoke({"question": transcript})
    except:
        args = MarketArgs(crop="tomato") # Fallback

    if "where" in transcript.lower() and "available" in transcript.lower():
        result = getCropLocations.invoke({"crop": args.crop})
    else:
        result = getMarketPrice.invoke({
            "crop": args.crop, 
            "location": args.location, 
            "state": args.state_name
        })
        
    return {"tool_data": result}


def disease_node(state: GraphState) -> GraphState:
    print("---DISEASE NODE---")
    if not os.path.exists(FIXED_IMAGE_PATH):
        return {"tool_data": "No image uploaded. Please upload an image of the affected plant."}
    
    transcript = state["transcript"].lower()
    if "wheat" in transcript:
        result = Wheat_disease_detection.invoke({})
    else:
        result = disease_Detect.invoke({})
        
    return {"tool_data": result}


def weather_node(state: GraphState) -> GraphState:
    print("---WEATHER NODE---")
    transcript = state["transcript"]
    
    structured_llm = Base_llm.with_structured_output(WeatherArgs)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract the Indian location/city from the query."),
        ("human", "{question}")
    ])
    chain = prompt | structured_llm
    try:
        args = chain.invoke({"question": transcript})
        loc = args.location
    except:
        loc = "Delhi" 
        
    result = Weather_tool.invoke({"location": loc})
    return {"tool_data": str(result)}


def scheme_node(state: GraphState) -> GraphState:
    print("---SCHEME NODE---")
    transcript = state["transcript"]
    
    if "detail" in transcript.lower() and "link" in transcript.lower():
        result = Find_scheme.invoke({})
    else:
        result = Find_scheme.invoke({})
        
    if isinstance(result, list):
        formatted = json.dumps(result[:5]) + f"\n... (and {len(result)-5} more)" if len(result) > 5 else json.dumps(result)
        return {"tool_data": f"Available schemes: {formatted}"}
        
    return {"tool_data": str(result)}


def chat_node(state: GraphState) -> GraphState:
    print("---CHAT NODE---")
    messages = state.get("messages", [])
    transcript = state["transcript"]
    intent = state.get("intent")
    tool_data = state.get("tool_data")
    language = state.get("language", "en")
    
    # 1. Prepare Prompt
    system_msg = """You are a helpful farming assistant named Krishi. 
    You have access to the following domains via tools:
    - Market: Crop prices (`call_market`)
    - Disease: Plant disease detection (`call_disease`)
    - Weather: Weather forecast (`call_weather`)
    - Scheme: Government schemes (`call_scheme`)
    
    Goal: Answer the user's question accurately.
    
    INSTRUCTIONS:
    1. **CHECK MEMORY**: Look at the conversation history. If the user refers to something mentioned previously (e.g., "what about for tomato?" referring to a location mentioned before), resolve it.
    2. **REFINE QUERY**: If you need to call a tool, generate a `refined_query` that is self-contained (includes location, crop, etc., from history).
    3. **DECIDE**:
        - If you HAVE `tool_data` clearly relevant to the question, USE IT to form your answer and set decision to 'respond'.
        - If you DO NOT have the data and the user is asking about prices, weather, schemes, or disease, choose 'call_X'.
        - If it is a general greeting or question you can answer from memory, set decision to 'respond'.
    
    Reply in the user's language if not English.
    """
    
    if tool_data:
        context_str = f"CURRENT TOOL DATA ({intent}):\n{tool_data}\n(Do not call the same tool again immediately unless necessary.)"
    else:
        context_str = "No tool data yet."
    
    # Format messages for context
    history_str = "\n".join([f"{m.type}: {m.content}" for m in messages])

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_msg),
        ("human", f"Conversation History:\n{history_str}\n\nContext:\n{context_str}\n\nUser Query: {transcript}")
    ])
    
    # 2. Invoke with Decision capability
    structured_llm = Base_llm.with_structured_output(ChatDecision)
    chain = chat_prompt | structured_llm
    
    try:
        result = chain.invoke({})
        decision = result.decision
        final_answer = result.final_response
        refined_query = result.refined_query
    except Exception as e:
        print(f"Chat decision error: {e}")
        decision = "respond"
        final_answer = "I'm having trouble processing that thought."
        refined_query = None

    print(f"Chat Decision: {decision}")

    if decision == "respond":
        if not final_answer:
            direct_response = Base_llm.invoke([
                SystemMessage(content=system_msg),
                HumanMessage(content=f"History: {history_str}\nContext: {context_str}\nUser: {transcript}")
            ])
            final_answer = direct_response.content

        new_history = messages + [HumanMessage(content=transcript), AIMessage(content=final_answer)]
        return {"response": final_answer, "messages": new_history, "intent": "end"}

    else:
        # Route to tool
        new_intent = decision.replace("call_", "")
        
        # If we have a refined query, update transcript so the tool sees the full context
        updates = {"intent": new_intent}
        if refined_query:
            print(f"Refining query: {transcript} -> {refined_query}")
            updates["transcript"] = refined_query
            
        return updates
