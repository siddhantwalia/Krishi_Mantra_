import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Literal, Optional
from utils.state import GraphState
from utils.llm import Base_llm
from utils.tools import getMarketPrice, getCropLocations, disease_Detect, Wheat_disease_detection, Find_scheme, Scheme_detials, Weather_tool, FIXED_IMAGE_PATH
import os
import re

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

# --- Nodes ---

def market_node(state: GraphState) -> GraphState:
    print("---MARKET NODE---")
    transcript = state["transcript"]
    messages = state.get("messages", [])
    history_str = "\n".join([f"{m.type}: {m.content}" for m in messages[-10:]]) # last 10 msgs
    
    # Extract args
    structured_llm = Base_llm.with_structured_output(MarketArgs)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract crop, location (district), and state from the user query. \n"
                   "IMPORTANT: Check the conversation history to resolve pronouns like 'this', 'it', or 'that' to specific crop names or locations mentioned earlier.\n"
                   "Default to empty string if not found."),
        ("human", "History:\n{history}\n\nCurrent Query: {question}")
    ])
    chain = prompt | structured_llm
    try:
        args = chain.invoke({"question": transcript, "history": history_str})
        if not args.crop: # Check if crop is empty string
             return {"tool_data": "MISSING_CROP: The user did not specify a crop. Please ask them which crop they are interested in."}
    except Exception as e:
        return {"tool_data": f"Error extracting parameters: {str(e)}"}

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
    # if "wheat" in transcript:
    result = Wheat_disease_detection.invoke({})
    # else:
        # result = disease_Detect.invoke({})
    os.remove(FIXED_IMAGE_PATH)    
    print(result)
    return {"tool_data": result}


def weather_node(state: GraphState) -> GraphState:
    print("---WEATHER NODE---")
    transcript = state["transcript"]
    messages = state.get("messages", [])
    history_str = "\n".join([f"{m.type}: {m.content}" for m in messages[-10:]])
    
    structured_llm = Base_llm.with_structured_output(WeatherArgs)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract the Indian location/city from the query.\n"
                   "IMPORTANT: Check conversation history if location is implied or mentioned previously."),
        ("human", "History:\n{history}\n\nCurrent Query: {question}")
    ])
    chain = prompt | structured_llm
    try:
        args = chain.invoke({"question": transcript, "history": history_str})
        loc = args.location
        if not loc:
             return {"tool_data": "MISSING_LOCATION: The user did not specify a location. Please ask them which city or district they are asking about."}
    except Exception as e:
         return {"tool_data": f"Error extracting parameters: {str(e)}"} 
        
    result = Weather_tool.invoke({"location": loc})
    return {"tool_data": str(result)}


def scheme_node(state: GraphState) -> GraphState:
    print("---SCHEME NODE---")
    transcript = state["transcript"]
    messages = state.get("messages", [])
    history_str = "\n".join([f"{m.type}: {m.content}" for m in messages[-10:]])
    
    # Optional: could update to extract args if Find_scheme supported params
    # For now, sticking to logic but ensuring context awareness isn't breaking anything
    # Scheme tool logic is simple now, but let's keep it robust.
    
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
    loop_step = state.get("loop_step", 0)
    if loop_step is None: loop_step = 0
    
    # --- LOOP PROTECTION ---
    if loop_step > 5:
        return {
            "response": "I'm sorry, I'm having trouble understanding. Could you please rephrase what you need clearly?",
            "messages": messages + [HumanMessage(content=transcript), AIMessage(content="Loop limit reached.")],
            "intent": "end",
            "loop_step": 0
        }

    # Increment step for this turn
    loop_step += 1

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
    1. **CHECK MEMORY**: Look at history. Resolve pronouns (e.g., "what about for tomato?").
    2. **HANDLE MISSING DATA**: 
       - If 'tool_data' starts with "MISSING_X" (e.g., MISSING_CROP, MISSING_LOCATION), your decision MUST be 'respond'.
       - In 'final_response', ask the user politely for the missing information.
    3. **DECIDE ACTION**:
        - 'respond': If you can answer (greeting, general info, clarifies missing info, or you have 'tool_data').
        - 'call_X': If you need data (market, weather, disease, scheme) and you have the necessary parameters.
    3. **OUTPUT JSON**:
    {{
      "decision": "respond" | "call_market" | "call_disease" | "call_weather" | "call_scheme",
      "final_response": "Your answer here (if decision is respond)",
      "refined_query": "Self-contained query for tool (if decision is call_X)"
    }}
    
    IMPORTANT: Do not output any thinking traces or tags like <think>...</think> in the final JSON. Output ONLY valid JSON.
    Reply in the user's language if not English.
    """
    
    if tool_data:
        context_str = f"CURRENT TOOL DATA ({intent}):\n{tool_data}\n(Do not call the same tool again immediately unless necessary.)"
    else:
        context_str = "No tool data yet."
    
    history_str = "\n".join([f"{m.type}: {m.content}" for m in messages])

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_msg),
        ("human", "Conversation History:\n{history}\n\nContext:\n{context}\n\nUser Query: {query}")
    ])
    
    # 2. Invoke MANUALLY (No structured_output wrapper)
    chain = chat_prompt | Base_llm
    
    decision = "respond"
    final_answer = ""
    refined_query = None

    try:
        response = chain.invoke({
            "history": history_str,
            "context": context_str,
            "query": transcript
        })
        content_text = response.content
        
        # --- ROBUSTNESS IMPROVEMENT ---
        # 1. Strip <think> tags if present in the raw output
        content_text = re.sub(r'<think>.*?</think>', '', content_text, flags=re.DOTALL).strip()
        
        # 2. Try to find JSON block using regex
        json_match = re.search(r'(\{.*\})', content_text, re.DOTALL)
        if json_match:
            clean_json = json_match.group(1)
        else:
            # Fallback to cleaning markdown
            clean_json = content_text.replace("```json", "").replace("```", "").strip()
        
        try:
            data = json.loads(clean_json)
            decision = data.get("decision", "respond")
            final_answer = data.get("final_response", "")
            refined_query = data.get("refined_query")
        except json.JSONDecodeError:
            print("JSON Parse Failed. Using Cleaned Text.")
            decision = "respond"
            final_answer = content_text # Use the text stripped of <think>

    except Exception as e:
        print(f"Chat execution error: {e}")
        decision = "respond"
        final_answer = "I'm having trouble processing that thought."

    print(f"Chat Decision: {decision}")

    if decision == "respond":
        # Final answer logic
        if not final_answer: 
             final_answer = "I'm here to help."
             
        new_history = messages + [HumanMessage(content=transcript), AIMessage(content=final_answer)]
        new_history = messages + [HumanMessage(content=transcript), AIMessage(content=final_answer)]
        return {"response": final_answer, "messages": new_history, "intent": "end", "loop_step": 0}

    else:
        # Route to tool
        new_intent = decision.replace("call_", "")
        updates = {"intent": new_intent, "loop_step": loop_step}
        if refined_query:
            print(f"Refining query: {transcript} -> {refined_query}")
            updates["transcript"] = refined_query
            
        return updates
