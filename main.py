from models import speech_to_text, text_to_speech
from utils import Base_llm, generate_1_res_prompt, tools
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, List
import json
import re

Audio_file = "farmer_response.mp3"

llm_with_tools = Base_llm.bind_tools(tools)

# -------------------------------
# Define State
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
    """Decides whether to use tools or respond directly"""
    try:
        # Ensure messages initialized
        if not state.get("messages"):
            state["messages"] = []

        # Add new user message
        state["messages"].append(HumanMessage(content=state["transcript"]))

        # Invoke tool-enabled LLM
        response = llm_with_tools.invoke(state["messages"])
        state["messages"].append(response)

        # If no tools are triggered, handle normal response
        if not (hasattr(response, 'tool_calls') and response.tool_calls):
            formatted_prompt = generate_1_res_prompt.format(
                transcript=state["transcript"],
                language=state["language"]
            )
            direct_response = Base_llm.invoke(state["messages"] + [HumanMessage(content=formatted_prompt)])
            resp_text = getattr(direct_response, "content", str(direct_response))

            try:
                parsed = json.loads(resp_text)
                state["response"] = parsed.get("response", resp_text)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*"response"\s*:\s*"([^"]*)".*\}', resp_text, re.DOTALL)
                if json_match:
                    state["response"] = json_match.group(1)
                else:
                    state["response"] = resp_text.strip()

            # Add AI reply to message history
            state["messages"].append(AIMessage(content=state["response"]))

    except Exception as e:
        print(f"Error in chat_node: {e}")
        fallback = (
            "मुझे खुशी होगी आपकी मदद करने में।"
            if state["language"] == "hindi"
            else "I'd be happy to help you with farming questions."
        )
        state["response"] = fallback

    return state


def process_tool_results(state: State) -> State:
    """Process tool outputs and create contextual reply"""
    try:
        tool_results = [msg.content for msg in state["messages"] if isinstance(msg, ToolMessage)]
        if tool_results:
            enhanced_transcript = f"{state['transcript']}\n\nAdditional information: {' | '.join(tool_results)}"

            formatted_prompt = generate_1_res_prompt.format(
                transcript=enhanced_transcript,
                language=state["language"]
            )
            response = Base_llm.invoke(state["messages"] + [HumanMessage(content=formatted_prompt)])
            resp_text = getattr(response, "content", str(response))

            try:
                parsed = json.loads(resp_text)
                state["response"] = parsed.get("response", resp_text)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*"response"\s*:\s*"([^"]*)".*\}', resp_text, re.DOTALL)
                if json_match:
                    state["response"] = json_match.group(1)
                else:
                    state["response"] = " | ".join(tool_results)

            state["messages"].append(AIMessage(content=state["response"]))

    except Exception as e:
        print(f"Error processing tool results: {e}")
        state["response"] = "I found some information but had trouble formatting it."

    return state

# -------------------------------
# Graph Logic
# -------------------------------
toolnode = ToolNode(tools)

def should_continue(state: State) -> str:
    if not state["messages"]:
        return END

    last_message = state["messages"][-1]

    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"

    tool_messages = [msg for msg in state["messages"] if isinstance(msg, ToolMessage)]
    if tool_messages and not state.get("response"):
        return "process_results"

    return END

# -------------------------------
# Build Graph
# -------------------------------
graph = StateGraph(State)
graph.add_node("chat", chat_node)
graph.add_node("tools", toolnode)
graph.add_node("process_results", process_tool_results)
graph.add_edge(START, "chat")
graph.add_conditional_edges("chat", should_continue)
graph.add_edge("tools", "process_results")
graph.add_edge("process_results", END)

# -------------------------------
# Add Checkpointer (Memory)
# -------------------------------
memory = MemorySaver()  # In-memory persistence (replaceable with Redis/SQLite)
chatbot = graph.compile(checkpointer=memory)

# -------------------------------
# Run pipeline
# -------------------------------
def get_response(user_input: str, language="English"):
    state = {
        "transcript": user_input,
        "language": language,
        "response": "",
        "messages": []  # No need to manually store messages anymore
    }

    thread_id = "farmer_session_1"  # unique session ID to persist conversation

    try:
        print(f"🤔 Processing: {state['transcript']}")
        final_state = chatbot.invoke(state, config={"configurable": {"thread_id": thread_id}})
        answer = final_state.get("response", "No response generated")
        print(answer)
        return answer

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return "Error processing request"

# Example usage
# get_response("I have a small piece of land and need a government scheme.")
# get_response("How can I check if I'm eligible?", language="English")
