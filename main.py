from models import speech_to_text, text_to_speech
from utils import Base_llm, generate_1_res_prompt,tools
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List
import json
import re

Audio_file = "farmer_response.mp3"

llm_with_tools = Base_llm.bind_tools(tools)

# -------------------------------
# State
# -------------------------------
class State(TypedDict):
    transcript: str      
    language: str       
    messages: List
    response: str

# -------------------------------
# Nodes
# -------------------------------
def chat_node(state: State) -> State:
    """Initial processing node - decides whether to use tools or respond directly"""
    try:
        # Initialize messages if empty
        if not state.get("messages"):
            state["messages"] = [HumanMessage(content=state["transcript"])]
        
        # Try tool-enabled LLM first
        try:
            response = llm_with_tools.invoke(state["messages"])
            state["messages"].append(response)
            
            # If no tool calls, generate direct response using your prompt
            if not (hasattr(response, 'tool_calls') and response.tool_calls):
                formatted_prompt = generate_1_res_prompt.format(
                    transcript=state["transcript"],
                    language=state["language"]
                )
                
                direct_response = Base_llm.invoke([HumanMessage(content=formatted_prompt)])
                resp_text = direct_response.content if hasattr(direct_response, "content") else str(direct_response)
                
                # Parse JSON response
                try:
                    parsed = json.loads(resp_text)
                    state["response"] = parsed.get("response", resp_text)
                except json.JSONDecodeError:
                    # Extract JSON with regex
                    json_match = re.search(r'\{.*"response"\s*:\s*"([^"]*)".*\}', resp_text, re.DOTALL)
                    if json_match:
                        state["response"] = json_match.group(1)
                    else:
                        state["response"] = resp_text.strip()
                
        except Exception as tool_error:
            print(f"Tool-enabled LLM failed: {tool_error}")
            # Fallback to direct prompt approach
            formatted_prompt = generate_1_res_prompt.format(
                transcript=state["transcript"],
                language=state["language"]
            )
            
            response = Base_llm.invoke([HumanMessage(content=formatted_prompt)])
            resp_text = response.content if hasattr(response, "content") else str(response)
            
            try:
                parsed = json.loads(resp_text)
                state["response"] = parsed.get("response", resp_text)
            except:
                state["response"] = resp_text
                
            state["messages"] = [HumanMessage(content=state["transcript"]), response]
        
    except Exception as e:
        print(f"Error in chat_node: {e}")
        fallback = "मुझे खुशी होगी आपकी मदद करने में।" if state["language"] == "hindi" else "I'd be happy to help you with farming questions."
        state["response"] = fallback
    
    return state

def process_tool_results(state: State) -> State:
    """Process tool results and generate final response using your prompt"""
    try:
        # Collect tool results
        tool_results = []
        for msg in state["messages"]:
            if isinstance(msg, ToolMessage):
                tool_results.append(msg.content)
        
        if tool_results:
            # Combine transcript with tool data
            enhanced_transcript = f"{state['transcript']}\n\nAdditional information: {' | '.join(tool_results)}"
            
            # Use your prompt template with enhanced context
            formatted_prompt = generate_1_res_prompt.format(
                transcript=enhanced_transcript,
                language=state["language"]
            )
            
            response = Base_llm.invoke([HumanMessage(content=formatted_prompt)])
            resp_text = response.content if hasattr(response, "content") else str(response)
            
            print("LLM raw output with tools:", resp_text)
            
            # Parse JSON response
            try:
                parsed = json.loads(resp_text)
                state["response"] = parsed.get("response", resp_text)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*"response"\s*:\s*"([^"]*)".*\}', resp_text, re.DOTALL)
                if json_match:
                    state["response"] = json_match.group(1)
                else:
                    state["response"] = " | ".join(tool_results)  # Fallback to raw tool results
            
            # Add final response to messages
            state["messages"].append(AIMessage(content=state["response"]))
        
    except Exception as e:
        print(f"Error processing tool results: {e}")
        state["response"] = "I found some information but had trouble formatting it."
    
    return state

# Tool node
toolnode = ToolNode(tools)

# -------------------------------
# Conditional Logic
# -------------------------------
def should_continue(state: State) -> str:
    """Determine next step based on conversation state"""
    if not state["messages"]:
        return END
    
    last_message = state["messages"][-1]
    
    # Check for tool calls
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        print(f"Tools to call: {[call['name'] for call in last_message.tool_calls]}")
        return "tools"
    
    # Check if we have tool results to process
    tool_messages = [msg for msg in state["messages"] if isinstance(msg, ToolMessage)]
    if tool_messages and not state.get("response"):
        return "process_results"
    
    print("Conversation complete")
    return END

# -------------------------------
# Graph with Tools
# -------------------------------
graph = StateGraph(State)
graph.add_node("chat", chat_node)
graph.add_node("tools", toolnode)
graph.add_node("process_results", process_tool_results)

# Edges
graph.add_edge(START, "chat")
graph.add_conditional_edges("chat", should_continue)
graph.add_edge("tools", "process_results")
graph.add_edge("process_results", END)

chatbot = graph.compile()

# -------------------------------
# Run pipeline
# -------------------------------
def get_response():
    Document = speech_to_text(Audio_file)
    state = {
        "transcript": Document.page_content,
        "language":Document.metadata['language'],
        "response": "",
        "messages": [] 
    }
    
    try:
        print(f"🤔 Processing: {state['transcript']}")
        final_state = chatbot.invoke(state)
        answer = final_state.get("response", "No response generated")
        
        audio = text_to_speech(answer)
        if audio:
            with open("response231311.mp3", "wb") as f:
                f.write(audio)
        
        return answer
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return "Error processing request"

if __name__ == "__main__":
    get_response()
