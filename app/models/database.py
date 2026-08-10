r"""Database connection and session management.

Set OPS_DB_PATH env var to use a shared network DB, e.g.:
  set OPS_DB_PATH=Z:\\shared\\ops_workbench.db
  or leave blank for local mode.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 优先使用环境变量指定的共享路径，否则用本地
_shared = os.environ.get("OPS_DB_PATH", "").strip()
if _shared:
    db_path = _shared
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
else:
    DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    os.makedirs(DB_DIR, exist_ok=True)
    db_path = os.path.join(DB_DIR, "ops_workbench.db")

DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=5,
    max_overflow=5,
    pool_timeout=30,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
