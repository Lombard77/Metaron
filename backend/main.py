from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime
import file_handler
import embedder 
from embedder import job_progress
import chat_engine
import logger
import json
import os
import re
import sqlite3
from pathlib import Path
from fastapi.responses import JSONResponse
from os import listdir
import shutil
import uuid
DB_PATH = "logs/metatron.db"

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("metatron")
log.info("🚀 Starting Metatron API server...")

logger.log_error("server", "Starting app")

app = FastAPI()

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
    goal_id: str  # ✅ goal_id replaces plan_name


# -------------------- AUTH --------------------
@app.post("/auth/register")
def register(user: UserCreate):
    try:
        log.info(f"📥 Register attempt: {user.email}")
        if logger.user_exists(user.email):
            raise HTTPException(status_code=400, detail="Email already registered")
        user_id = logger.create_user(user.email, user.password, user.first_name, user.last_name, user.age_group)
        log.info(f"✅ Registered: {user.email} → {user_id}")
        return {"message": "User registered successfully", "user_id": user_id}

    except Exception as e:
        logger.log_error("auth/register", str(e))
        log.error(f"❌ Register failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/auth/login")
def login(user: UserLogin):
    try:
        log.info(f"🔐 Login attempt: {user.email}")

        if not logger.user_exists(user.email):
            raise HTTPException(status_code=404, detail="User not found")

        if not logger.validate_login(user.email, user.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id = logger.get_user_id_by_email(user.email)
        if not user_id:
            raise HTTPException(status_code=500, detail="User ID missing")

        log.info(f"✅ Login successful: {user.email} → {user_id}")
        return {"message": "Login successful", "user_id": user_id}

    except Exception as e:
        logger.log_error("auth/login", str(e))
        log.error(f"❌ Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login error")
    
@app.get("/auth/profile")
def get_user_profile_endpoint(user_id: str):
    try:
        log.info(f"👤 Fetching profile for user_id: {user_id}")
        profile = logger.get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        return profile
    except Exception as e:
        logger.log_error("auth/profile", str(e))
        log.error(f"❌ Profile fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch profile")


# -------------------- UPLOAD --------------------
@app.post("/upload")
def upload_file(email: str = Form(...), plan_name: str = Form(...), file: UploadFile = File(...)):
    try:
        log.info(f"📤 Upload request for: {plan_name} by {email}")
        file_handler.process_file(file, plan_name, email)
        logger.log_uploaded_files(email, [file.filename])
        return {"message": "File uploaded and processed"}
    except Exception as e:
        logger.log_error("upload", str(e))
        log.error(f"❌ Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Upload failed")

# -------------------- CREATE PLAN --------------------
@app.post("/create-plan")
def create_plan(email: str = Form(...), plan_name: str = Form(...)):
    try:
        log.info(f"🛠 Creating plan: {plan_name} for {email}")
        embedder.embed_and_store(plan_name, email)
        logger.log_uploaded_files(email, ["[embedding complete]"])
        return {"message": "Plan created"}
    except Exception as e:
        logger.log_error("create-plan", str(e))
        log.error(f"❌ Plan creation error: {str(e)}")
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
    files: List[UploadFile] = File(None),
    existing_files: str = Form("")  # JSON string like '["fileA.txt", "fileB.txt"]'
):
    log.info(f"🧾 Raw existing_files field: {existing_files}")

    try:
        log.info(f"📁 Coaching goal upload: {goal_name} for {user_id}")
        goal_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()

        # ⬇️ Save goal metadata in goals table (new feature)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO goals (goal_id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (goal_id, user_id, goal_name, created_at, created_at))
        conn.commit()
        conn.close()
        kb_path = Path("data/vector_store") / goal_id  # ✅ Use goal_id instead of goal_name
        kb_path.mkdir(parents=True, exist_ok=True)

        is_edit = kb_path.exists()
        saved_filenames = []
        # Parse and track preserved files
        try:
            preserved_files = json.loads(existing_files)
            if not isinstance(preserved_files, list):
                raise ValueError("existing_files is not a list")
        except Exception as e:
            logger.log_error("upload-kb", f"💥 Failed to parse existing_files: {existing_files} ({str(e)})")
            raise HTTPException(status_code=400, detail="Invalid existing_files format")

        saved_filenames.extend(preserved_files)

        # Save new uploads
        if files:
            for file in files:
                file_path = kb_path / file.filename
                with open(file_path, "wb") as f:
                    f.write(await file.read())
                saved_filenames.append(file.filename)

        # Merge old + new for embedding
        combined_text = ""
        all_files = list(set(preserved_files + saved_filenames))  # ✅ Prevent duplicates
        log.info(f"📦 Files to merge for embedding: {all_files}")
        for file in all_files:

            path = kb_path / file
            try:
                if path.exists():
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        combined_text += f.read() + "\n"
            except Exception as read_err:
                log.warning(f"⚠️ Could not read file {file}: {read_err}")

        log.info(f"🔍 combined_text length: {len(combined_text)}")
        if not combined_text.strip():
            raise HTTPException(status_code=400, detail="No readable content found in uploaded files.")


        
        if combined_text.strip():
            job_id = str(uuid.uuid4())  # ✅ generate unique ID
            log.info(f"🚨 Created job_id: {job_id}")
            embedder.embed_and_store(combined_text, goal_id, provider, api_key, job_id=job_id)  # ✅ pass job_id
            log.info(f"🧠 Embedded: {goal_name} with {len(existing_files) + len(saved_filenames)} files")


        # Detect diffs for logging
        removed_set = set(preserved_files) - set(saved_filenames)
        logger.log_file_diff(f"{user_id}_{goal_name}", saved_filenames, list(removed_set))


        logger.log_uploaded_files(f"{user_id}_{goal_name}", saved_filenames)

        # Audit file diff
        if is_edit:
            old_set = set(preserved_files)
            new_set = set(f.filename for f in files) if files else set()
            logger.log_file_diff(f"{user_id}_{goal_name}", list(new_set), list(set(existing_files) - old_set))


        logger.save_kb_metadata(
            goal_id=goal_id,
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
            "goal_id": goal_id,
            "goal": goal_name,
            "files": preserved_files + saved_filenames,
            "action": "updated" if is_edit else "created",
            "job_id": job_id  # ✅ this is the real one created earlier
        }


    except Exception as e:
        logger.log_error("upload-kb", str(e))
        log.error(f"❌ Upload-KB error: {str(e)}")
        raise HTTPException(status_code=500, detail="Upload failed")

# -------------------- ASK --------------------
@app.post("/ask")
def ask_question(request: QuestionRequest):
    try:
        log.info(f"🧠 Ask: {request.question} on {request.goal_id} by {request.email}")
        response = chat_engine.ask_question(request.goal_id, request.question)
        logger.log_chat(request.goal_id, request.question, response)  # ✅ also updated below

        return {"answer": response}
    except Exception as e:
        logger.log_error("ask", str(e))
        log.error(f"❌ Ask error: {str(e)}")
        raise HTTPException(status_code=500, detail="Question failed")

# -------------------- LIST COACHING GOALS --------------------
@app.get("/goals")
def get_goals(user_id: str):
    try:
        log.info(f"📋 Fetching goals for: {user_id}")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute('''
            SELECT goal_id, kb_name, intent, timeframe_value, goal_description
            FROM kb_meta
            WHERE user_id = ?
            ORDER BY last_accessed_at DESC
        ''', (user_id,))
        
        rows = c.fetchall()
        conn.close()

        if not rows:
            log.info(f"📭 No goals found for user_id: {user_id}")
            return JSONResponse(content={"goals": []})  # ✅ graceful fallback

        goals = []
        for row in rows:
            goal_id = row[0]
            kb_name = row[1]
            intent = row[2]
            timeframe = row[3]
            description = row[4]
            goal_folder = Path("data/vector_store") / goal_id
            file_list = []

            if goal_folder.exists():
                file_list = [{
                    "name": f,
                    "size": (goal_folder / f).stat().st_size
                } for f in listdir(goal_folder) if (goal_folder / f).is_file()]

            goals.append({
                "goal_id": goal_id,
                "title": kb_name,
                "intent": intent,
                "timeframe": timeframe,
                "description": description,
                "files": file_list
            })

        return JSONResponse(content={"goals": goals})

    except Exception as e:
        logger.log_error("goals", str(e))
        log.error(f"❌ Goal fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load goals")


# -------------------- START SESSION --------------------
@app.post("/start-session")
def start_session(goal_id: str = Form(...)):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT kb_name, user_id FROM kb_meta WHERE goal_id = ?", (goal_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        kb_name, user_id = row
        log.info(f"🚀 Starting session: {kb_name} for {user_id}")
        return {
            "status": "ok",
            "message": f"Session started for '{kb_name}'",
            "goal_id": goal_id
        }
    except Exception as e:
        logger.log_error("start-session", str(e))
        log.error(f"❌ Start-session error: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not start session")


# -------------------- HEALTH CHECK --------------------
@app.get("/")
def root():
    return {"message": "Metatron API is alive"}

@app.get("/job-status")
def get_job_status(job_id: str):
    """
    Return real-time status for the given job_id from the backend embedding pipeline.
    """
    if not job_id:
        return {"status": "missing"}

    status = job_progress.get(job_id)
    if status:
        return {"status": status}
    else:
        return {"status": "waiting"}


# -------------------------------
# 🛑 Coaching Goal Cancel Logging
# -------------------------------

@app.post("/cancel-goal")
def cancel_goal(user_id: str = Form(...), goal_name: str = Form(...)):
    try:
        log.warning(f"🛑 User {user_id} cancelled goal creation/edit: {goal_name}")
        logger.log_event("cancel-goal", f"{user_id} cancelled {goal_name}")
        return {"status": "ok", "message": "Cancel logged"}
    except Exception as e:
        logger.log_error("cancel-goal", str(e))
        log.error(f"❌ Cancel logging error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to log cancel")

class DeleteGoalRequest(BaseModel):
    goal_id: str  # ✅ Using canonical goal_id only

@app.post("/delete-goal")
def delete_goal(data: DeleteGoalRequest, request: Request):
    goal_id = data.goal_id
    log.warning(f"🗑️ Request to delete goal_id: {goal_id}")

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # ✅ Fetch goal info for audit
        c.execute("SELECT kb_name, user_id FROM kb_meta WHERE goal_id = ?", (goal_id,))
        row = c.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Goal not found in kb_meta")
        kb_name, user_id = row

        # ✅ Delete from kb_meta
        c.execute("DELETE FROM kb_meta WHERE goal_id = ?", (goal_id,))
        
        # ✅ Delete from goals table
        c.execute("DELETE FROM goals WHERE goal_id = ?", (goal_id,))

        # ✅ Optional: Delete from chat_log if table exists
        try:
            c.execute("DELETE FROM chat_log WHERE goal_id = ?", (goal_id,))
        except Exception as chatlog_err:
            log.warning(f"⚠️ Skipped chat_log cleanup: {chatlog_err}")

        conn.commit()

        # ✅ Delete vector store folder
        goal_path = Path("data/vector_store") / goal_id
        if goal_path.exists():
            shutil.rmtree(goal_path)
            log.info(f"🧹 Deleted folder: {goal_path}")
        else:
            log.warning(f"⚠️ Vector folder not found for goal_id: {goal_id}")

        conn.close()

        # ✅ Audit log
        logger.log_event("delete-goal", f"Deleted goal_id: {goal_id} (User: {user_id}, Name: {kb_name})")

        return {"status": "ok", "message": f"Goal '{kb_name}' fully deleted"}

    except Exception as e:
        logger.log_error("delete-goal", str(e))
        log.error(f"❌ Failed to delete goal: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete goal")
    
