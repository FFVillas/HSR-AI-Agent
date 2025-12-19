import os
import re
import asyncio
from typing import List
from langchain_core.tools import tool
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.pinecone import PineconeVectorStore
from pinecone import Pinecone
from tavily import AsyncTavilyClient
from backend.app.prompts import RAG_TOOL_DESC, BROWSE_TOOL_DESC, READ_KNOWLEDGE_DESC
from dotenv import load_dotenv
load_dotenv()

# --- SETUP PINECONE ---
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
pinecone_index = pc.Index("honkai-star-rail-agent")
vector_store = PineconeVectorStore(pinecone_index=pinecone_index, namespace="character-knowledge")
embed_model = GoogleGenAIEmbedding(model="models/embedding-001")

index = VectorStoreIndex.from_vector_store(vector_store=vector_store, embed_model=embed_model)
retriever = index.as_retriever(similarity_top_k=5)

# --- SETUP TAVILY ---
tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Clean browse content
def clean_search_content(raw_content: str) -> str:
    """
    Cleans raw web search content by removing image links,
    markdown artifacts, duplicate lines, and excess whitespace.
    """
    lines = raw_content.split('\n')
    cleaned_lines = []
    seen_lines = set()

    for line in lines:
        # Turns '![The Remembrance](...url...)' into 'The Remembrance'
        line = re.sub(r'!?\[([^\]]*)\]\([^)]+\)', r'\1', line)

        # Strip whitespace from the line
        line = line.strip()

        # Skip empty lines or lines that become empty after cleaning
        if not line:
            continue

        # Skip duplicate lines
        if line not in seen_lines:
            seen_lines.add(line)
            cleaned_lines.append(line)
            
    return '\n'.join(cleaned_lines)

# TOOLS

@tool(description=RAG_TOOL_DESC)
def RAG_tool(query: str) -> str:
    """Retrieves official game data."""
    response = retriever.retrieve(query)
    return "\n\n".join([doc.text for doc in response])

@tool(description=BROWSE_TOOL_DESC)
async def browse_tool(queries: List[str]) -> str:
    """Performs parallel web searches with cleaning."""
    # Create search tasks
    tasks = [
        tavily_client.search(
            query=q, 
            search_depth="advanced", 
            max_results=3, 
            include_raw_content=True,
            exclude_domains=["youtube.com"]
        ) 
        for q in queries
    ]
    
    results_list = await asyncio.gather(*tasks)
    
    clean_output = []
    for i, res in enumerate(results_list):
        clean_output.append(f"--- Results for '{queries[i]}' ---")
        for item in res.get("results", []):
            # Use the helper function here
            raw = item.get("raw_content", "") or item.get("content", "")
            content = clean_search_content(raw)
            url = item.get("url", "")
            clean_output.append(f"Content from {url}\n{content}\n")
            
    return "\n".join(clean_output)

@tool(description=READ_KNOWLEDGE_DESC)
def read_knowledge_tool(reasoning: str) -> str:
    """
    Placeholder function - logic is handled in the graph node.
    
    Args:
        reasoning: Explain strictly why you need to read the knowledge now.
    """