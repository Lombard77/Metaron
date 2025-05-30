from sqlmodel import SQLModel, Field
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime


# 📘 Master Prompt
class MasterPrompt(SQLModel, table=True):
    __tablename__ = "master_prompts"
    master_prompt_id: UUID = Field(primary_key=True)
    template: str
    version: int
    description: Optional[str] = None


# 🧠 Goal-Specific Prompt
class GoalPrompt(SQLModel, table=True):
    __tablename__ = "goal_prompts"
    goal_prompt_id: UUID = Field(primary_key=True)
    goal_id: UUID
    prompt_snippet: str
    override_base: bool
    version: int


# 🧩 Goal Plan (Tiered Learning Structure)
class GoalPlan(SQLModel, table=True):
    __tablename__ = "goal_plans"
    goal_plan_id: UUID = Field(primary_key=True)
    goal_id: UUID
    plan_version: int
    topics: Dict
    milestones: List[str]
    tier_structure: Dict
    summary: Optional[str] = None


# 📊 Learner Progress Snapshots
class ProgressSnapshot(SQLModel, table=True):
    __tablename__ = "progress_snapshots"
    snapshot_id: UUID = Field(primary_key=True)
    goal_id: UUID
    user_id: UUID
    timestamp: datetime
    content_score: Optional[float] = None
    cycle_stage: Optional[str] = None
    topic_status: Optional[Dict[str, str]] = None
    notes: Optional[str] = None
    quiz_summary: Optional[str] = None
    engagement_score: Optional[float] = None


# 👤 User Context
class UserMeta(SQLModel, table=True):
    __tablename__ = "user_meta"
    user_id: UUID = Field(primary_key=True)
    first_name: str
    language_pref: Optional[str] = None
    last_topic_viewed: Optional[str] = None


# 💬 Chat Session Meta
class ChatSessionMeta(SQLModel, table=True):
    __tablename__ = "chat_session_meta"
    chat_session_id: UUID = Field(primary_key=True)
    goal_id: UUID
    compiled_prompt: str
    compiled_at: datetime
    prompt_version: int


# 📂 Compiled Prompts
class CompiledPrompt(SQLModel, table=True):
    __tablename__ = "compiled_prompts"
    compiled_prompt_id: UUID = Field(primary_key=True)
    chat_session_id: UUID
    goal_id: UUID
    prompt_text: str
    inputs_used: Dict
    engine_name: str
    template_id: UUID
    debug_trace: Optional[Dict] = None


# 📄 Upload Logs
class UploadLog(SQLModel, table=True):
    __tablename__ = "uploads"
    timestamp: Optional[str] = None
    session_id: Optional[str] = None
    filename: Optional[str] = None


# 💬 Chat Logs
class ChatLog(SQLModel, table=True):
    __tablename__ = "logs"
    timestamp: Optional[str] = None
    session_id: Optional[str] = None
    question: Optional[str] = None
    response: Optional[str] = None


# 📁 Knowledge Base Metadata
class KnowledgeBaseMeta(SQLModel, table=True):
    __tablename__ = "kb_meta"
    id: Optional[str] = Field(default=None, primary_key=True)
    organization_id: Optional[str] = None
    team_leader_id: Optional[str] = None
    user_id: Optional[str] = None
    kb_name: Optional[str] = None
    intent: Optional[str] = None
    timeframe_type: Optional[str] = None
    timeframe_value: Optional[str] = None
    goal_description: Optional[str] = None
    created_at: Optional[str] = None
    last_accessed_at: Optional[str] = None
    goal_id: Optional[str] = None
    model: Optional[str] = None


# 👤 User Account
class UserAccount(SQLModel, table=True):
    __tablename__ = "users"
    email: Optional[str] = None
    password_hash: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age_group: Optional[str] = None
    created_at: Optional[datetime] = None
    role: Optional[str] = None
    user_id: Optional[str] = Field(default=None, primary_key=True)
    organization_id: Optional[str] = None
    team_leader_id: Optional[str] = None


# 🎯 Coaching Goals
class Goal(SQLModel, table=True):
    __tablename__ = "goals"
    goal_id: Optional[str] = Field(default=None, primary_key=True)
    user_id: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
