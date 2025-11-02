from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import traceback
from main import chatbot    

app = FastAPI(
    title="Farming Chatbot API",
    description="API interface for the LangGraph-based farming assistant chatbot.",
    version="1.0"
)


class ChatRequest(BaseModel):
    transcript: str
    language: Optional[str] = "English"
    thread_id : str


@app.get("/")
def home():
    return {"message": "Backend working..."}


@app.get("/health")
def health():
    return {"status": "healthy"}

from langgraph.types import RunnableConfig

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    try:
        thread_id = request.thread_id

        # Load previous state if available
        prev_state = chatbot.get_state(
            config={"configurable": {"thread_id": thread_id}}
        )

        # Use previous messages if found, else start fresh
        messages = prev_state.values.get("messages", []) if prev_state else []

        # Create new state using previous context
        state = {
            "transcript": request.transcript,
            "language": request.language,
            "response": "",
            "messages": messages
        }

        print(f"🤔 Processing: {state['transcript']}")
        final_state = chatbot.invoke(
            state,
            config=RunnableConfig(configurable={"thread_id": thread_id})
        )

        answer = final_state.get("response", "No response generated")

        return {"success": True, "response": answer}

    except Exception as e:
        print("Error during /chat:", e)
        traceback.print_exc()
        return {"success": False, "error": str(e)}
