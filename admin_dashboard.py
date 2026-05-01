import streamlit as st
import os
from database import SessionLocal, APIKey, ChatSession, ChatMessage
import uuid
import shutil
from core_logic import update_vector_store

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
            db.refresh(new_key)
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
    st.write("Upload PDF documents to train your chatbot for a specific client.")
    
    db = get_db_session()
    keys = db.query(APIKey).all()
    
    if not keys:
        st.warning("Please create an API Key in 'Manage API Keys' first.")
    else:
        # Create a mapping of display name to ID
        client_options = {f"{k.owner_name} (ID: {k.id})": k.id for k in keys}
        selected_client_name = st.selectbox("Select Client", list(client_options.keys()))
        selected_client_id = client_options[selected_client_name]
        
        urls_input = st.text_area("Website URLs (one per line, optional)", help="The AI will scrape and learn from these URLs.")
        uploaded_files = st.file_uploader(f"Choose Documents for {selected_client_name.split(' (')[0]}", type=["pdf", "txt", "docx", "csv"], accept_multiple_files=True)
        
        if st.button("Upload & Train"):
            if uploaded_files or urls_input.strip():
                client_knowledge_dir = os.path.join("knowledge", str(selected_client_id))
                os.makedirs(client_knowledge_dir, exist_ok=True)
                
                for file in uploaded_files:
                    with open(os.path.join(client_knowledge_dir, file.name), "wb") as f:
                        f.write(file.getbuffer())
                
                if urls_input.strip():
                    cleaned_urls = []
                    for line in urls_input.split('\n'):
                        line = line.strip()
                        if line:
                            if not line.startswith('http'):
                                line = 'http://' + line
                            cleaned_urls.append(line)
                    with open(os.path.join(client_knowledge_dir, "urls.txt"), "w", encoding="utf-8") as f:
                        f.write('\n'.join(cleaned_urls))
                
                with st.spinner("Training Vector Store..."):
                    try:
                        update_vector_store(selected_client_id)
                        st.success("Knowledge Base updated successfully! The AI has been trained for this client.")
                    except Exception as e:
                        st.error(f"Failed to train: {str(e)}")
            else:
                st.warning("Please select files or enter URLs first.")
    db.close()