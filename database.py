from sqlmodel import create_engine, Session, SQLModel
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# For Vercel deployments, we should use a PostgreSQL database
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
        "pool_size": 5,  # Smaller pool size for serverless
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_timeout": 30,
        "echo": True  # Enable for debugging
    }
else:
    # For SQLite in serverless, we don't need pooling
    # But we should still set echo for debugging
    pool_kwargs = {
        "echo": True,  # Enable for debugging
        "poolclass": None  # No pooling for SQLite
    }

# For serverless, we need to handle the database URL properly
# If using PostgreSQL, ensure SSL is handled properly
if DATABASE_URL.startswith("postgresql"):
    # Add SSL requirements for production databases like Neon
    if "sslmode" not in DATABASE_URL.lower():
        DATABASE_URL += "?sslmode=require"

engine = create_engine(DATABASE_URL, connect_args=connect_args, **pool_kwargs)

def create_db_and_tables():
    # Import all models before creating tables
    from models import Task, User
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
