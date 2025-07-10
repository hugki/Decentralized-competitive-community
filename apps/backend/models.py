from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, Column, text
from sqlalchemy import func, Float, DateTime

class TaskStatus(str, Enum):
    QUEUED   = "QUEUED"
    RUNNING  = "RUNNING"
    DONE     = "DONE"
    DISPUTED = "DISPUTED"

# ---------- core tables ---------- #

class Model(SQLModel, table=True):
    __tablename__ = "model"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    hf_repo: str = Field()
    submitter_github: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        sa_column=Column(
            "created_at",
            DateTime,
            server_default=text("now()")
        )
    )


class Benchmark(SQLModel, table=True):
    __tablename__ = "benchmark"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    version: str
    dataset_sha: str


class Task(SQLModel, table=True):
    __tablename__ = "task"

    id: str = Field(primary_key=True, index=True)  # UUID (cli 側生成)
    model_id: int = Field(foreign_key="model.id")
    benchmark_id: int = Field(foreign_key="benchmark.id")
    status: TaskStatus = Field(
        sa_column=Column("status", nullable=False)
    )
    assigned_to: Optional[str] = Field(default=None, index=True)
    score: Optional[float] = Field(sa_column=Column(Float))
    runtime_sec: Optional[int] = Field(default=None)

    created_at: datetime = Field(
        sa_column=Column(
            "created_at",
            DateTime,
            server_default=text("now()")
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            "updated_at",
            DateTime,
            server_default=text("now()"),
            onupdate=func.now(),
        )
    )


class TaskResult(SQLModel, table=True):
    """各 runner の投票（K 件収集して consensus）"""
    __tablename__ = "task_result"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: str = Field(foreign_key="task.id", index=True)
    runner_id: str
    score: float
    runtime_sec: int
    stdout_sha: str
    created_at: datetime = Field(
        sa_column=Column(
            "created_at",
            DateTime,
            server_default=text("now()")
        )
    )

# ---------- readonly materialized view ---------- #

class LeaderboardHourly(SQLModel, table=True):
    """
    PostgreSQL 側で
        CREATE MATERIALIZED VIEW leaderboard_hourly AS …
    を実行しておき、ここでは read‑only マッピング。
    """
    __tablename__ = "leaderboard_hourly"
    __table_args__ = {"autoload_with": None}  # Alembic にスキップさせる

    id: Optional[int] = Field(primary_key=True)
    name: str
    avg_score: float
    last_eval: datetime
