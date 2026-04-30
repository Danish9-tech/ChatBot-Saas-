@echo off
echo Starting SaaS Chatbot Services...

REM Start FastAPI Server in the background
start "FastAPI Server" cmd /c "uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait a couple seconds
timeout /t 3 /nobreak > nul

REM Start Streamlit Admin Dashboard
start "Admin Dashboard" cmd /c "streamlit run admin_dashboard.py"

echo Services started!
echo ------------------------------------------
echo API Server: http://localhost:8000
echo Admin Dashboard: http://localhost:8501
echo ------------------------------------------
pause
