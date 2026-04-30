import streamlit as st
import os
from database import SessionLocal, APIKey, ChatSession, ChatMessage
import uuid
import shutil

st.set_page_config(page_title="Chatbot Admin Dashboard", page_icon="⚙️", layout="wide")
st.title("⚙️ SaaS Admin Dashboard")

# Navigation
page = st.sidebar.radio("Navigate", ["Manage API Keys", "View Chat Logs", "Knowledge Base"])

def get_db_session():
    return SessionLocal()

if page == "Manage API Keys":
    st.header("🔑 API Keys & Clients")
    
    with st.form("new_key_form"):
        owner_name = st.text_input("Client / Owner Name")
        submit = st.form_submit_button("Generate New API Key")
        
        if submit and owner_name:
            db = get_db_session()
            new_key = APIKey(owner_name=owner_name)
            db.add(new_key)
            db.commit()
            st.success(f"Generated new key for {owner_name}: `{new_key.key}`")
            db.close()
            
    st.subheader("Existing Keys")
    db = get_db_session()
    keys = db.query(APIKey).all()
    if keys:
        for k in keys:
            st.write(f"**{k.owner_name}**: `{k.key}` (Created: {k.created_at})")
    else:
        st.info("No API keys found.")
    db.close()

elif page == "View Chat Logs":
    st.header("📜 Chat Logs")
    db = get_db_session()
    sessions = db.query(ChatSession).all()
    
    if not sessions:
        st.info("No chat sessions found.")
    else:
        session_id = st.selectbox("Select Session", [s.id for s in sessions])
        if session_id:
            messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
            for msg in messages:
                role = "🧑 User" if msg.sender == "user" else "🤖 Bot"
                st.markdown(f"**{role}**: {msg.message}")
    db.close()

elif page == "Knowledge Base":
    st.header("📚 Upload Knowledge Documents")
    st.write("Upload PDF documents to train your chatbot.")
    
    uploaded_files = st.file_uploader("Choose PDFs", type="pdf", accept_multiple_files=True)
    if st.button("Upload & Train"):
        if uploaded_files:
            os.makedirs("knowledge", exist_ok=True)
            for file in uploaded_files:
                with open(os.path.join("knowledge", file.name), "wb") as f:
                    f.write(file.getbuffer())
            st.success("Files uploaded successfully! The vector store will automatically use them on the next query/startup.")
        else:
            st.warning("Please select files first.")