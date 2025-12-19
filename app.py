import streamlit as st
import requests
import json

API_URL = st.secrets.get("BACKEND_API_URL", "http://127.0.0.1:8000/chat")
PAGE_TITLE = "HSR Knowledge Agent"

USER_AVATAR = "User_Avatar.png" 
AI_AVATAR = "AI_Avatar.png"
st.set_page_config(page_title=PAGE_TITLE, page_icon="🎮")

# --- REMOVED CUSTOM CSS ---
# We removed the st.markdown block to restore default Streamlit UI (Right/Left alignment)

# --- HEADER ---
st.title(f"{PAGE_TITLE}")
st.caption("Made with LangGraph, Pinecone, and Gemini :D")

# --- SIDEBAR ---
with st.sidebar:
    st.header("About")
    st.markdown("Portfolio demo using RAG + Agents.")
    st.markdown("Rate limit will reset every 16:00 UTC+8")
    st.divider()
    if st.button("Clear History"):
        st.session_state.messages = []
        st.rerun()

# --- STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 1. HANDLE INPUT ---
if prompt := st.chat_input("Ask about characters, builds, lightcones...", max_chars=1000):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Display
for message in st.session_state.messages:
    if message["role"] == "error":
        st.error(message["content"])
    else:
        avatar_img = USER_AVATAR if message["role"] == "user" else AI_AVATAR
        with st.chat_message(message["role"], avatar=avatar_img):
            st.markdown(message["content"])
            # Show steps in expander if they exist
            if "steps" in message and message["steps"]:
                with st.expander("Process Details"):
                    for step in message["steps"]:
                        st.markdown(step)

# Response
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    
    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        
        with status_placeholder.container():
            status_box = st.status("Thinking...", expanded=False)

        response_placeholder = st.empty()
        steps_placeholder = st.empty()

        full_response = ""
        collected_steps = []
        is_first_token = True

        try:
            user_msg = st.session_state.messages[-1]["content"]
            
            # Request to backend API with streaming
            with requests.post(API_URL, json={"message": user_msg}, stream=True) as response:
                if response.status_code == 200:
                    
                    # Iterate over the stream line by line
                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            try:
                                data = json.loads(decoded_line)
                                type_ = data.get("type")
                                content = data.get("content")
                                
                                if type_ == "step":
                                    # Update the label to show what it is doing (e.g. "Used Tool: Google")
                                    status_box.update(label=f"Thinking... {content}", state="running")
                                    collected_steps.append(content)
                                    
                                elif type_ == "token":
                                    # If this is the VERY first text token, close the status box
                                    if is_first_token:
                                        status_placeholder.empty()
                                        is_first_token = False
                                    
                                    full_response += content
                                    response_placeholder.markdown(full_response + "▌")
                                    
                            except json.JSONDecodeError:
                                continue

                    # Final render without cursor
                    response_placeholder.markdown(full_response)

                    # Show steps at the bottom in an expander after done
                    if collected_steps:
                        with steps_placeholder.expander("Process Details", expanded=False):
                            for step in collected_steps:
                                st.markdown(step)

                    # Save to history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": full_response,
                        "steps": collected_steps 
                    })
                    
                elif response.status_code == 429:
                    st.session_state.messages.append({"role": "error", "content": "Traffic Limit Reached."})
                    st.rerun()
                else:
                    st.session_state.messages.append({"role": "error", "content": f"Error: {response.text}"})
                    st.rerun()
                    
        except Exception as e:
            st.session_state.messages.append({"role": "error", "content": f"Connection Error: {e}"})
            st.rerun()