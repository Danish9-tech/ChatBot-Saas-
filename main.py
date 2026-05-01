from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from database import get_db, APIKey, ChatSession, ChatMessage
from core_logic import get_conversational_response, get_vector_store

app = FastAPI(title="University Help Desk SaaS API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow any website to embed the widget
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the widget
app.mount("/public", StaticFiles(directory="public"), name="public")

@app.get("/")
def read_root():
    return RedirectResponse(url="/public/index.html")

# Vector stores are now initialized dynamically per API Key on demand

# Models
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class MessageModel(BaseModel):
    sender: str
    message: str

class ChatResponse(BaseModel):
    answer: str
    session_id: str

def verify_api_key(x_api_key: str = Header(...), db: Session = Depends(get_db)):
    api_key = db.query(APIKey).filter(APIKey.key == x_api_key).first()
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, api_key: APIKey = Depends(verify_api_key), db: Session = Depends(get_db)):
    # Get or create session
    if request.session_id:
        chat_session = db.query(ChatSession).filter(ChatSession.id == request.session_id, ChatSession.api_key_id == api_key.id).first()
        if not chat_session:
            chat_session = ChatSession(id=request.session_id, api_key_id=api_key.id)
            db.add(chat_session)
            db.commit()
    else:
        chat_session = ChatSession(api_key_id=api_key.id)
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

    # Reconstruct memory from DB
    db_messages = db.query(ChatMessage).filter(ChatMessage.session_id == chat_session.id).order_by(ChatMessage.created_at).all()
    chat_memory = []
    # pair them up loosely
    temp_q = None
    for msg in db_messages:
        if msg.sender == "user":
            temp_q = msg.message
        elif msg.sender == "bot" and temp_q:
            chat_memory.append((temp_q, msg.message))
            temp_q = None

    # Get response
    vectorstore = get_vector_store(api_key.id)
    answer, _ = get_conversational_response(
        query=request.query, 
        chat_memory=chat_memory, 
        vectorstore=vectorstore, 
        client_name=api_key.owner_name or "our service"
    )

    # Save to DB
    user_msg = ChatMessage(session_id=chat_session.id, sender="user", message=request.query)
    bot_msg = ChatMessage(session_id=chat_session.id, sender="bot", message=answer)
    
    db.add(user_msg)
    db.add(bot_msg)
    db.commit()

    return ChatResponse(answer=answer, session_id=chat_session.id)

@app.get("/api/v1/history", response_model=List[MessageModel])
async def get_history(session_id: str, api_key: APIKey = Depends(verify_api_key), db: Session = Depends(get_db)):
    chat_session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.api_key_id == api_key.id).first()
    if not chat_session:
        return []
    
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
    return [{"sender": m.sender, "message": m.message} for m in messages]
