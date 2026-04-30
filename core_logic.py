import os
import json
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables. Please check your .env file.")

# Initialize Models
embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GOOGLE_API_KEY
)

llm = ChatGoogleGenerativeAI(
    model="models/gemini-flash-latest",
    temperature=0.3,
    google_api_key=GOOGLE_API_KEY
)

def load_knowledge_base():
    """Load knowledge.json"""
    knowledge_file = "knowledge.json"
    try:
        if os.path.exists(knowledge_file):
            with open(knowledge_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading knowledge file: {e}")
        return []

def load_and_split_pdfs(folder_path="knowledge"):
    """Load PDF documents from folder"""
    docs = []
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(folder_path, filename)
                loader = PyPDFLoader(pdf_path)
                docs.extend(loader.load())
    except Exception as e:
        print(f"Error loading PDFs: {e}")

    if docs:
        splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        return splitter.split_documents(docs)
    return []

def initialize_vector_store():
    """Initialize FAISS vector store"""
    try:
        docs = load_and_split_pdfs("knowledge")
        if docs:
            vectorstore = FAISS.from_documents(docs, embedding_model)
            return vectorstore
        return None
    except Exception as e:
        print(f"Error creating vector store: {e}")
        return None

restrict_prompt = ChatPromptTemplate.from_template("""
You are a friendly and helpful University Help Desk Assistant for Iqra University (Airport Campus).
Rules:
- Only answer university-related questions (admissions, exams, courses, fees, schedules, faculty, hostel, campus services, campus locations).
- If the question is unrelated, reply exactly: "❌ Sorry, I can only help with university-related queries."
- Keep your answers short, concise, and structured in a human-like manner.
- Do NOT use raw markdown formatting, asterisks (*), or bold text. Use plain text formatting.
Question: {question}
""")

def get_conversational_response(query: str, chat_memory: list = None, vectorstore=None) -> tuple[str, list]:
    """Get response from conversational chain"""
    if chat_memory is None:
        chat_memory = []
        
    try:
        # Step 1: Check if question is university-related
        raw_restricted = llm.invoke(restrict_prompt.format(question=query)).content
        if isinstance(raw_restricted, list):
            restricted_answer = "".join([r.get("text", "") for r in raw_restricted if r.get("type") == "text"])
        else:
            restricted_answer = str(raw_restricted)

        if "❌" in restricted_answer:
            return restricted_answer, chat_memory

        # Step 2: Try PDF retrieval if available
        pdf_answer = ""
        if vectorstore:
            try:
                docs = vectorstore.similarity_search(query, k=3)
                if docs:
                    context = "\n".join([d.page_content for d in docs])
                    retrieval_prompt = f"""Based on the following information, answer the question in a friendly, conversational manner. Keep the answer short and directly useful. Do NOT use any markdown symbols like asterisks (*) or bold text.

Information:
{context}

Question: {query}

Answer:"""
                    response = llm.invoke(retrieval_prompt).content
                    if isinstance(response, list):
                        pdf_answer = "".join([r.get("text", "") for r in response if r.get("type") == "text"]).strip()
                    else:
                        pdf_answer = str(response).strip()
            except Exception as e:
                print(f"Retrieval error: {e}")
                pdf_answer = ""

        # Step 3: Decide response
        weak_pdf = (
            not pdf_answer
            or "i don't know" in pdf_answer.lower()
            or "not included" in pdf_answer.lower()
            or "does not contain" in pdf_answer.lower()
            or "not available" in pdf_answer.lower()
            or "sorry" in pdf_answer.lower()
        )

        if weak_pdf:
            # Maybe fallback to knowledge.json matching
            kb = load_knowledge_base()
            kb_answer = None
            q_lower = query.lower()
            for entry in kb:
                if any(kw.lower() in q_lower for kw in entry.get("keywords", [])):
                    kb_answer = entry.get("answer")
                    break
            
            if kb_answer:
                response = kb_answer
            else:
                general_prompt = f"""
You are a friendly University Help Desk Assistant for Iqra University.

Question: {query}

Important Rules:
- Keep the response short, human-like, and highly structured.
- Do NOT use markdown symbols, asterisks (*), or bold text. Use plain text formatting.
- Do NOT reply with "I don't know" or "I'm sorry".
- Provide a helpful, generic, university-style answer tailored to Iqra University.
- Use natural phrases like: "Usually, universities require..." or "Typically, students need to..."

Answer:
"""
                raw_response = llm.invoke(general_prompt).content
                if isinstance(raw_response, list):
                    response = "".join([r.get("text", "") for r in raw_response if r.get("type") == "text"])
                else:
                    response = str(raw_response)
        else:
            response = str(pdf_answer)

        chat_memory.append((query, response))
        return response, chat_memory
    except Exception as e:
        print(f"Error generating response: {e}")
        return "❌ Sorry, I encountered an error. Please try again.", chat_memory
