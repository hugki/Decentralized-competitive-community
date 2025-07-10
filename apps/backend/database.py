from contextlib import asynccontextmanager
from sqlmodel import SQLModel, create_engine, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local.db")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

def init_db() -> None:
    """Local‑only helper (`sqlite`)—prod は Alembic migration で作成"""
    SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def get_session():
    with Session(engine) as session:
        yield session
