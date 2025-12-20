# HSR-AI-Agent

This is a personal project of an AI agent designed to help players of **Honkai Star Rail** answer questions about characters, builds, and ect.
I built this project just as a fun work on summer break. I first made this in Jupyter Notebook and moved it to Python so i can demo it.

You can try out the live demo right here: https://huggingface.co/spaces/FFVillas/hsr-chat

## How It Works

### Backend
- A **FastAPI** server running **LangGraph**
- Handles logic, tool usage, and state management

### Frontend
- A **Streamlit** interface

### Tools

I gave the agent just two tools
- RAG tool (which contains in-game informations like stats, levelups, materials, for now i only put character and lightcone informations. The RAG has information until version 3.4)
- Browse tool using Tavily API


## Tech Stack

- **Language:** Python 3.11  
- **Orchestration:** LangGraph, LangChain
- **Backend:** FastAPI, Uvicorn  
- **Frontend:** Streamlit  
- **Database:** Pinecone / Chroma, Llamaindex (for RAG indexing & retrieval)
- **AI Models:** Google Gemini 1.5 Flash  
- **Deployment:** Docker, Hugging Face Spaces

---

## Getting Started

If you want to run this locally, follow these steps.

### Ennviornment

You will need to put some API keys in your .env:

- Gemini API (or any LLM API, but you need to change the code)
- Pinecone (Or change it to local vector database)
- Tavily
- Langsmith, if you want to trace the agent

### Installation

1.  Clone this repository to your machine.
2.  Create a virtual environment to keep things clean.
3.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Create a `.env` file in the main folder and add your keys:
    ```text
    GOOGLE_API_KEY=your_key_here
    PINECONE_API_KEY=your_key_here
    TAVILY_API_KEY=your_key_here
    ```

### Running the App

You will need two terminal windows because the frontend and backend run separately.

**Terminal 1 (Backend):**
```bash
  uvicorn main:app --port 8000
```
**Terminal 2 (Backend):**
```bash
  streamlit run src/app.py
```

Then open the URL in the streamlit terminal.
