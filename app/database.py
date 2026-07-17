import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Locate and parse runtime configurations
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tri9t_compliance.db")

# 'check_same_thread' is required exclusively for SQLite to map across async endpoints safely
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency injection helper to yield database session lifetimes cleanly."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()