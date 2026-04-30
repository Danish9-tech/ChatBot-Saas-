# 🚀 SaaS Chatbot Setup & Integration Guide

Welcome to the new, modernized SaaS Chatbot system. This project has been transformed from a single Streamlit script into a full-fledged API with an embeddable website widget and an admin control panel.

## 🛠️ Installation & Setup

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Install Dependencies
Make sure you are in the project root directory (`Chatbot`), then install the required Python packages:

```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory if you haven't already:

```env
GOOGLE_API_KEY=your-google-gemini-api-key-here
```

### 4. Running the System
We have provided a convenient batch script to launch both the backend API and the admin dashboard at the same time:

```bash
run.bat
```
- **FastAPI Backend** runs on `http://localhost:8000`
- **Streamlit Admin Dashboard** runs on `http://localhost:8501`

---

## 🔑 Managing API Keys & Clients

1. Open the **Admin Dashboard** (`http://localhost:8501`).
2. Navigate to **"Manage API Keys"** from the sidebar.
3. Enter a client/owner name and click **Generate New API Key**.
4. Copy the generated key. You will need to provide this key to your clients so they can embed the widget.

---

## 🌐 Website Integration

To add the chatbot to **any website**, the website owner simply needs to add the following `<script>` tag right before the closing `</body>` tag of their HTML pages.

```html
<script src="http://localhost:8000/public/chatbot.js" data-api-key="THEIR_API_KEY_HERE"></script>
```

> **Note:** If you deploy this to a live server (e.g., Vercel, Render, AWS), replace `http://localhost:8000` with your actual production domain.

---

## 📚 Knowledge Base Management

1. Open the **Admin Dashboard**.
2. Navigate to **"Knowledge Base"**.
3. Upload any relevant PDF files.
4. The system will automatically process, chunk, and embed the PDFs into the FAISS vector store.

---

## 🏗️ Architecture Overview

- **`main.py`**: The FastAPI backend. Exposes `/api/v1/chat` and `/api/v1/history`.
- **`core_logic.py`**: Contains the LangChain, FAISS, and Gemini logic.
- **`database.py`**: SQLAlchemy models for API Keys, Sessions, and Messages (stored in SQLite).
- **`admin_dashboard.py`**: The Streamlit interface for system administration.
- **`public/chatbot.js`**: The vanilla JavaScript widget injected into client websites.
- **`public/chatbot.css`**: The modern styling for the widget.
