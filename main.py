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
    """Handles chat logic, uses memory for contextual responses."""
    try:
        # Initialize message list
        if not state.get("messages"):
            state["messages"] = []

        # Add new user message
        state["messages"].append(HumanMessage(content=state["transcript"]))

        # Invoke LLM with tool awareness
        response = llm_with_tools.invoke(state["messages"])
        state["messages"].append(response)

        # Handle direct chat if no tools are called
        if not (hasattr(response, "tool_calls") and response.tool_calls):
            # Build conversation history using memory
            conversation_history = "\n".join(
                f"{type(msg).__name__}: {getattr(msg, 'content', '')}"
                for msg in state["messages"]
            )

            # Inject memory dynamically into the prompt
            memory_aware_prompt = generate_1_res_prompt.partial(
                conversation_history=conversation_history
            ).format(
                transcript=state["transcript"],
                language=state["language"]
            )

            # Pass the state (memory) explicitly to LLM
            direct_response = Base_llm.invoke(
                state["messages"] + [HumanMessage(content=memory_aware_prompt)]
            )

            resp_text = getattr(direct_response, "content", str(direct_response))

            # Parse JSON-formatted response
            try:
                parsed = json.loads(resp_text)
                state["response"] = parsed.get("response", resp_text)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*"response"\s*:\s*"([^"]*)".*\}', resp_text, re.DOTALL)
                if json_match:
                    state["response"] = json_match.group(1)
                else:
                    state["response"] = resp_text.strip()

            # Append model's reply to memory
            state["messages"].append(AIMessage(content=state["response"]))

    except Exception as e:
        print(f"Error in chat_node: {e}")
        fallback = (
            "मुझे खुशी होगी आपकी मदद करने में।"
            if state["language"].lower() == "hindi"
            else "I'd be happy to help you with farming questions."
        )
        state["response"] = fallback

    return state


def process_tool_results(state: State) -> State:
    """Process tool outputs and provide contextual answer."""
    try:
        tool_results = [msg.content for msg in state["messages"] if isinstance(msg, ToolMessage)]
        print(tool_results)
        if tool_results:
            enhanced_transcript = f"{state['transcript']}\n\nAdditional info: {' | '.join(tool_results)}"

            # Build history using memory
            conversation_history = "\n".join(
                f"{type(msg).__name__}: {getattr(msg, 'content', '')}"
                for msg in state["messages"]
            )

            memory_prompt = generate_1_res_prompt.partial(
                conversation_history=conversation_history
            ).format(
                transcript=enhanced_transcript,
                language=state["language"]
            )

            response = Base_llm.invoke(state["messages"] + [HumanMessage(content=memory_prompt)])
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
    """Control flow logic for LangGraph."""
    if not state["messages"]:
        return END

    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    tool_messages = [msg for msg in state["messages"] if isinstance(msg, ToolMessage)]
    if tool_messages and not state.get("response"):
        return "process_results"

    return END


# -------------------------------
# Build Graph with Memory
# -------------------------------
graph = StateGraph(State)
graph.add_node("chat", chat_node)
graph.add_node("tools", toolnode)
graph.add_node("process_results", process_tool_results)
graph.add_edge(START, "chat")
graph.add_conditional_edges("chat", should_continue)
graph.add_edge("tools", "process_results")
graph.add_edge("process_results", END)

# 🧠 MemorySaver provides in-memory conversation persistence
memory = MemorySaver()
chatbot = graph.compile(checkpointer=memory)

# -------------------------------
# Run pipeline with persistent memory
# -------------------------------
def get_response(user_input: str, language="English"):
    state = {
        "transcript": user_input,
        "language": language,
        "response": "",
        "messages": []  # Automatically restored from MemorySaver
    }

    # Use a unique session key to retain conversation across turns
    thread_id = "farmer_session_1"

    try:
        print(f"🤔 Processing: {state['transcript']}")
        final_state = chatbot.invoke(state, config={"configurable": {"thread_id": thread_id}})

        answer = final_state.get("response", "No response generated")
        print(f"✅ Response: {answer}")
        return answer

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return "Error processing request"
