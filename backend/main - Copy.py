from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import sqlite3
import auth
import file_handler
import embedder
import chat_engine
import logger

# Initialize DB
auth.init_db()

app = FastAPI()

# -------------------- CORS --------------------
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
    if auth.user_exists(user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    auth.create_user(user.email, user.password, user.first_name, user.last_name, user.age_group)
    return {"message": "User registered successfully"}

@app.post("/auth/login")
def login(user: UserLogin):
    if not auth.user_exists(user.email):
        raise HTTPException(status_code=404, detail="User not found")
    if not auth.validate_login(user.email, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful"}

# -------------------- UPLOAD --------------------
@app.post("/upload")
def upload_file(email: str = Form(...), plan_name: str = Form(...), file: UploadFile = File(...)):
    file_handler.process_file(file, plan_name, email)
    logger.log_uploaded_files(email, plan_name, file.filename)
    return {"message": "File uploaded and processed"}

# -------------------- CREATE PLAN --------------------
@app.post("/create-plan")
def create_plan(email: str = Form(...), plan_name: str = Form(...)):
    embedder.embed_and_store(plan_name, email)
    logger.log_uploaded_files(email, plan_name, "[embedding complete]")
    return {"message": "Plan created"}

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
    files: List[UploadFile] = File(...)
):
    from pathlib import Path
    import os
    import re

    sanitized_goal_name = re.sub(r'[^a-zA-Z0-9._-]', '_', goal_name.strip())
    kb_path = Path("data/vector_store") / sanitized_goal_name
    kb_path.mkdir(parents=True, exist_ok=True)

    saved_filenames = []
    for file in files:
        file_path = kb_path / file.filename
        with open(file_path, "wb") as f:
            f.write(await file.read())
        saved_filenames.append(file.filename)

    combined_text = ""
    for file in saved_filenames:
        path = kb_path / file
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            combined_text += f.read() + "\n"

    embedder.embed_and_store(combined_text, sanitized_goal_name, provider, api_key)

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
        "files": saved_filenames
    }

# -------------------- ASK --------------------
@app.post("/ask")
def ask_question(request: QuestionRequest):
    response = chat_engine.ask_question(request.email, request.plan_name, request.question)
    logger.log_chat(request.email, request.plan_name, request.question, response)
    return {"answer": response}

# -------------------- LIST COACHING GOALS --------------------
@app.get("/goals")
def get_goals(user_id: str):
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

# -------------------- HEALTH CHECK --------------------
@app.get("/")
def root():
    return {"message": "Metatron API is alive"}
