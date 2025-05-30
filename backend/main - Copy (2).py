from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import file_handler
import embedder
import chat_engine
import logger
import os
import re
import sqlite3
from pathlib import Path
from fastapi.responses import JSONResponse

logger.log_error("server", "Starting app")

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- MODELS --------------------
class UserCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    age_group: str

class UserLogin(BaseModel):
    email: str
    password: str

class QuestionRequest(BaseModel):
    email: str
    question: str
    plan_name: str

# -------------------- AUTH --------------------
@app.post("/auth/register")
def register(user: UserCreate):
    try:
        if logger.user_exists(user.email):
            raise HTTPException(status_code=400, detail="Email already registered")
        logger.create_user(user.email, user.password, user.first_name, user.last_name, user.age_group)
        return {"message": "User registered successfully"}
    except Exception as e:
        logger.log_error("auth/register", str(e))
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/auth/login")
def login(user: UserLogin):
    try:
        if not logger.user_exists(user.email):
            raise HTTPException(status_code=404, detail="User not found")
        if not logger.validate_login(user.email, user.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"message": "Login successful"}
    except Exception as e:
        logger.log_error("auth/login", str(e))
        raise HTTPException(status_code=500, detail="Login error")

# -------------------- UPLOAD --------------------
@app.post("/upload")
def upload_file(email: str = Form(...), plan_name: str = Form(...), file: UploadFile = File(...)):
    try:
        file_handler.process_file(file, plan_name, email)
        logger.log_uploaded_files(email, [file.filename])
        return {"message": "File uploaded and processed"}
    except Exception as e:
        logger.log_error("upload", str(e))
        raise HTTPException(status_code=500, detail="Upload failed")

# -------------------- CREATE PLAN --------------------
@app.post("/create-plan")
def create_plan(email: str = Form(...), plan_name: str = Form(...)):
    try:
        embedder.embed_and_store(plan_name, email)
        logger.log_uploaded_files(email, ["[embedding complete]"])
        return {"message": "Plan created"}
    except Exception as e:
        logger.log_error("create-plan", str(e))
        raise HTTPException(status_code=500, detail="Plan creation failed")

# -------------------- UPLOAD COACHING GOAL --------------------
@app.post("/upload-kb")
async def upload_kb(
    goal_name: str = Form(...),
    intent: str = Form(...),
    timeframe: str = Form(...),
    description: str = Form(...),
    provider: str = Form(...),
    api_key: str = Form(None),
    user_id: str = Form(...),
    files: List[UploadFile] = File(None)
):
    try:
        sanitized_goal_name = re.sub(r'[^a-zA-Z0-9._-]', '_', goal_name.strip())
        kb_path = Path("data/vector_store") / sanitized_goal_name
        kb_path.mkdir(parents=True, exist_ok=True)

        is_edit = kb_path.exists()
        saved_filenames = []

        if files:
            for file in files:
                file_path = kb_path / file.filename
                with open(file_path, "wb") as f:
                    f.write(await file.read())
                saved_filenames.append(file.filename)

        if saved_filenames:
            combined_text = ""
            for file in saved_filenames:
                path = kb_path / file
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    combined_text += f.read() + "\n"
            embedder.embed_and_store(combined_text, sanitized_goal_name, provider, api_key)

        logger.log_uploaded_files(f"{user_id}_{goal_name}", saved_filenames)

        logger.save_kb_metadata(
            org_id="",
            team_leader_id="",
            user_id=user_id,
            kb_name=goal_name,
            intent=intent,
            timeframe_type="custom",
            timeframe_value=timeframe,
            goal_description=description
        )

        return {
            "status": "ok",
            "goal": goal_name,
            "files": saved_filenames,
            "action": "updated" if is_edit else "created"
        }

    except Exception as e:
        logger.log_error("upload-kb", str(e))
        raise HTTPException(status_code=500, detail="Upload failed")

# -------------------- ASK --------------------
@app.post("/ask")
def ask_question(request: QuestionRequest):
    try:
        response = chat_engine.ask_question(request.email, request.plan_name, request.question)
        logger.log_chat(request.email, request.question, response)
        return {"answer": response}
    except Exception as e:
        logger.log_error("ask", str(e))
        raise HTTPException(status_code=500, detail="Question failed")

# -------------------- LIST COACHING GOALS --------------------
@app.get("/goals")
def get_goals(user_id: str):
    try:
        conn = sqlite3.connect("logs/chat_logs.db")
        c = conn.cursor()
        c.execute('''
            SELECT kb_name, intent, timeframe_value, goal_description
            FROM kb_meta
            WHERE user_id = ?
            ORDER BY last_accessed_at DESC
        ''', (user_id,))
        rows = c.fetchall()
        conn.close()

        goals = []
        for row in rows:
            goals.append({
                "id": f"{user_id}_{row[0]}",
                "title": row[0],
                "intent": row[1],
                "timeframe": row[2],
                "description": row[3]
            })

        return JSONResponse(content={"goals": goals})
    except Exception as e:
        logger.log_error("goals", str(e))
        raise HTTPException(status_code=500, detail="Failed to load goals")

# -------------------- START SESSION --------------------
@app.post("/start-session")
def start_session(user_id: str = Form(...), goal_name: str = Form(...)):
    try:
        return {
            "status": "ok",
            "message": f"Session started for '{goal_name}'",
            "goal_id": f"{user_id}_{goal_name}"
        }
    except Exception as e:
        logger.log_error("start-session", str(e))
        raise HTTPException(status_code=500, detail="Could not start session")

# -------------------- HEALTH CHECK --------------------
@app.get("/")
def root():
    return {"message": "Metatron API is alive"}
