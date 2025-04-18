import streamlit as st  
import requests, uuid, os  
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/chat")  
  
# ───────────────── Sidebar ──────────────────  
with st.sidebar:  
    st.title("⚙️  Controls")  
    if st.button("🗘  New chat", key="new_chat"):  
        st.session_state["messages"]   = []  
        st.session_state["session_id"] = str(uuid.uuid4())  
        st.success("Started a brand‑new chat session!")  
  
# ───────────────── Page title ────────────────  
st.markdown(  
    "<h1 style='display:flex; align-items:center;'>AI Chat Assistant 🤖</h1>",  
    unsafe_allow_html=True,  
)  
  
# ───────────────── Chat history ─────────────  
if "session_id" not in st.session_state:  
    st.session_state["session_id"] = str(uuid.uuid4())  
if "messages" not in st.session_state:  
    st.session_state["messages"] = []  
  
for msg in st.session_state["messages"]:  
    with st.chat_message(msg["role"]):  
        st.markdown(msg["content"])  
  
prompt = st.chat_input("Type a message...")  
if prompt:  
    st.session_state["messages"].append({"role": "user", "content": prompt})  
    with st.chat_message("user"):  
        st.markdown(prompt)  
  
    with st.spinner("Assistant is thinking..."):  
        r = requests.post(  
            BACKEND_URL,  
            json={"session_id": st.session_state["session_id"], "prompt": prompt},  
        )  
        r.raise_for_status()  
        answer = r.json()["response"]  
  
    st.session_state["messages"].append({"role": "assistant", "content": answer})  
    with st.chat_message("assistant"):  
        st.markdown(answer)  