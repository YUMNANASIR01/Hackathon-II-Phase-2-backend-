from sqlmodel import create_engine, Session, SQLModel
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default to a file-based SQLite database if DATABASE_URL is not set
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tasks.db")

# Adjust connect_args based on the database type
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# For PostgreSQL, we don't need special connect_args, but we'll set pool settings
pool_kwargs = {}
if DATABASE_URL.startswith("postgresql"):
    pool_kwargs = {
        "pool_size": 20,
        "max_overflow": 0,
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args, **pool_kwargs)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
