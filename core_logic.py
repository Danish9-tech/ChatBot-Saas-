import os
from langchain_community.vectorstores import PGVector
from database import get_db_connection_string
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader, Docx2txtLoader, WebBaseLoader
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

def load_and_split_documents(folder_path):
    """Load various documents from folder and URLs"""
    docs = []
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if filename.lower().endswith(".pdf"):
                docs.extend(PyPDFLoader(file_path).load())
            elif filename.lower().endswith(".txt") and filename.lower() != "urls.txt":
                docs.extend(TextLoader(file_path, encoding='utf-8').load())
            elif filename.lower().endswith(".csv"):
                docs.extend(CSVLoader(file_path, encoding='utf-8').load())
            elif filename.lower().endswith(".docx"):
                docs.extend(Docx2txtLoader(file_path).load())
            elif filename.lower() == "urls.txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    urls = [line.strip() for line in f.readlines() if line.strip()]
                if urls:
                    try:
                        docs.extend(WebBaseLoader(urls).load())
                    except Exception as ue:
                        print(f"Error scraping URLs: {ue}")
    except Exception as e:
        print(f"Error loading documents from {folder_path}: {e}")

    if docs:
        splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        return splitter.split_documents(docs)
    return []

def get_vector_store(api_key_id: int):
    """Retrieve vector store for a specific client from Supabase"""
    connection_string = get_db_connection_string(for_sqlalchemy=True)
    try:
        vectorstore = PGVector(
            collection_name=f"client_{api_key_id}",
            connection_string=connection_string,
            embedding_function=embedding_model,
        )
        return vectorstore
    except Exception as e:
        print(f"Error connecting to PGVector for {api_key_id}: {e}")
        return None

def update_vector_store(api_key_id: int):
    """Force rebuild the vector store for a specific client"""
    folder_path = os.path.join("knowledge", str(api_key_id))
    docs = load_and_split_documents(folder_path)
    if not docs:
        raise ValueError("No valid text could be extracted from the provided files or URLs.")
    
    try:
        connection_string = get_db_connection_string(for_sqlalchemy=True)
        # Delete old collection to prevent duplicates and insert new docs
        PGVector.from_documents(
            documents=docs,
            embedding=embedding_model,
            collection_name=f"client_{api_key_id}",
            connection_string=connection_string,
            pre_delete_collection=True
        )
    except Exception as e:
        print(f"Error updating PGVector index for {api_key_id}: {e}")
        raise RuntimeError(f"Database error while saving knowledge: {str(e)}")

restrict_prompt = ChatPromptTemplate.from_template("""
You are a friendly and helpful Assistant for {client_name}.
Rules:
- Only answer questions related to {client_name}'s domain and services.
- If the question is completely unrelated, reply exactly: "❌ Sorry, I can only help with queries related to {client_name}."
- Keep your answers short, concise, and structured in a human-like manner.
- Do NOT use raw markdown formatting, asterisks (*), or bold text. Use plain text formatting.
Question: {question}
""")

def get_conversational_response(query: str, chat_memory: list = None, vectorstore=None, client_name: str = "our service") -> tuple[str, list]:
    """Get response from conversational chain"""
    if chat_memory is None:
        chat_memory = []
        
    try:
        # Step 1: Check if question is related to client's domain
        raw_restricted = llm.invoke(restrict_prompt.format(client_name=client_name, question=query)).content
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
            general_prompt = f"""
You are a friendly Help Desk Assistant for {client_name}.

Question: {query}

Important Rules:
- Keep the response short, human-like, and highly structured.
- Do NOT use markdown symbols, asterisks (*), or bold text. Use plain text formatting.
- Provide a helpful, generic answer tailored to {client_name}.

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
