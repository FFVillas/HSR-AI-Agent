import os
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.app.agent import agent_app
from langchain_core.messages import HumanMessage

# Setup Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="HSR Agent API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class ChatRequest(BaseModel):
    message: str

async def generate_chat_stream(message: str):
    """
    Generator function that runs the agent and yields data chunks:
    - {"type": "step", "content": "Tool Name"}
    - {"type": "token", "content": "text chunk"}
    """
    initial_state = {"messages": [HumanMessage(content=message)], "knowledge": []}
    
    # We use astream_events to get granular control over tools and tokens
    # version="v2" is required for LangChain > 0.2
    async for event in agent_app.astream_events(initial_state, version="v1"):
        event_type = event["event"]
        
        # 1. Capture Tool Usage (Steps)
        if event_type == "on_tool_start":
            tool_name = event["name"]
            # Filter out internal wrapper tools if necessary
            if tool_name not in ["_Exception", "LangGraph"]: 
                step_data = json.dumps({"type": "step", "content": f"🛠️ Used Tool: {tool_name}"})
                yield f"{step_data}\n"

        # 2. Capture Streaming Tokens (The Answer)
        elif event_type == "on_chat_model_stream":
            # Only stream tokens from the final node (the "llm_call" that generates the answer)
            # We filter by the node name defined in your agent.py
            if event["metadata"].get("langgraph_node") == "llm_call":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    # Handle cases where content might be a list (Gemini 3 quirk), though usually string in stream
                    content = chunk.content
                    if isinstance(content, list):
                        # Extract text if it's a rich content list
                        text_content = "".join([item['text'] for item in content if 'text' in item])
                    else:
                        text_content = str(content)
                        
                    if text_content:
                        token_data = json.dumps({"type": "token", "content": text_content})
                        yield f"{token_data}\n"

@app.post("/chat")
@limiter.limit("4/minute")
async def chat(request: Request, chat_req: ChatRequest):
    # Input validation
    if len(chat_req.message) > 1000:
        raise HTTPException(status_code=400, detail="Message too long. Max 1000 characters.")

    try:
        return StreamingResponse(
            generate_chat_stream(chat_req.message), 
            media_type="application/x-ndjson"
        )

    except Exception as e:
        error_msg = str(e)
        print(f"Server Error: {error_msg}")
        raise HTTPException(status_code=500, detail=str(e))