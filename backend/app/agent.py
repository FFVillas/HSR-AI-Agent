import inspect
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END, START

from backend.app.state import AgentState
from backend.app.tools import RAG_tool, browse_tool, read_knowledge_tool
from backend.app.prompts import AGENT_SYSTEM_PROMPT, PRUNING_PROMPT

# 1. Setup Models
# Main Agent Brain
llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", thinking_level="low")
# The "Pruner" LLM
summarization_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0, thinking_budget=0)

# Bind tools
tools = [RAG_tool, browse_tool, read_knowledge_tool]
tools_by_name = {t.name: t for t in tools}
llm_with_tools = llm.bind_tools(tools)

# 2. Define Nodes

def llm_call(state: AgentState):
    """The Decision Maker"""
    # Prepend System Prompt
    messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

async def tool_node(state: AgentState):
    """The Tool Executor + Pruner"""
    tool_messages = []
    knowledge_updates = []
    
    last_message = state["messages"][-1]
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool = tools_by_name[tool_name]
        
        # --- SPECIAL CASE: Read Knowledge ---
        if tool_name == "read_knowledge_tool":
            # Access the accumulated knowledge from state
            notes = state.get("knowledge", [])
            consolidated = "\n\n".join(notes) if notes else "No knowledge gathered yet."
            
            tool_messages.append(ToolMessage(
                content=f"--- FACT SHEET ---\n{consolidated}", 
                tool_call_id=tool_call["id"],
                name=tool_name
            ))
            
        # --- STANDARD CASE: RAG or Browse ---
        else:
            # 1. Execute Tool
            if inspect.iscoroutinefunction(tool.ainvoke):
                raw_result = await tool.ainvoke(tool_call["args"])
            else:
                raw_result = tool.invoke(tool_call["args"])
            
            # 2. Prune/Summarize (Your Notebook Logic)
            pruning_msg = await summarization_llm.ainvoke([
                SystemMessage(content=PRUNING_PROMPT),
                {"role": "user", "content": str(raw_result)}
            ])
            pruned_text = pruning_msg.content
            
            # 3. Update State
            tool_messages.append(ToolMessage(
                content=pruned_text, 
                tool_call_id=tool_call["id"], 
                name=tool_name
            ))
            # Add to 'knowledge' list
            knowledge_updates.append(pruned_text)

    return {
        "messages": tool_messages,
        "knowledge": knowledge_updates
    }

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tool_node"
    return END

# 3. Build Graph
builder = StateGraph(AgentState)
builder.add_node("llm_call", llm_call)
builder.add_node("tool_node", tool_node)

builder.add_edge(START, "llm_call")
builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
builder.add_edge("tool_node", "llm_call")

agent_app = builder.compile()