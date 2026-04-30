from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import uuid

DATABASE_URL = "sqlite:///./chatbot.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    owner_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chats = relationship("ChatSession", back_populates="api_key")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    api_key_id = Column(Integer, ForeignKey("api_keys.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    api_key = relationship("APIKey", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"))
    sender = Column(String) # "user" or "bot"
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("ChatSession", back_populates="messages")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
