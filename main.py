from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from typing import List
from uuid import UUID
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import crud
from models import TaskRead, TaskCreate, TaskUpdate, UserRead, UserCreate, UserLogin, TokenResponse, TaskListResponse
from database import get_session, create_db_and_tables
from security import verify_access_token, create_access_token, verify_password

app = FastAPI(title="Todo App API", version="1.0.0")

# Add CORS middleware
import os
frontend_url = os.getenv("FRONTEND_URL", "").strip()

# Build allowed origins list
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "https://localhost:3000",
    "https://hackathon-2-phase-2-one.vercel.app",  # Production frontend
]

# Add production frontend URL from env if set and not already in list
if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

# For debugging: print CORS origins
print(f"[CORS Config] Frontend URL from env: {frontend_url}")
print(f"[CORS Config] Allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT verification dependency
def get_current_user(token: str = None) -> UUID:
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    # Extract token from "Bearer <token>" format
    if token.startswith("Bearer "):
        token = token[7:]

    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_id

# Override get_current_user to extract from headers
from fastapi import Header
def get_current_user_from_header(authorization: str = Header(None)) -> UUID:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = authorization
    if token.startswith("Bearer "):
        token = token[7:]

    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_id

# Only run database initialization in non-serverless environments
# For Vercel serverless functions, database setup should be handled separately
import os

if os.getenv("VERCEL", "false").lower() != "1":
    @app.on_event("startup")
    def on_startup():
        create_db_and_tables()

# Authentication Endpoints
@app.post("/api/auth/signup", response_model=TokenResponse)
def signup(user: UserCreate, db: Session = Depends(get_session)):
    try:
        db_user = crud.get_user_by_email(db, email=user.email)
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        new_user = crud.create_user(db, user=user)
        access_token = create_access_token(new_user.id)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserRead(
                id=new_user.id,
                email=new_user.email,
                name=new_user.name,
                created_at=new_user.created_at
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Signup error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")

@app.post("/api/auth/signin", response_model=TokenResponse)
def signin(credentials: UserLogin, db: Session = Depends(get_session)):
    db_user = crud.get_user_by_email(db, email=credentials.email)
    if not db_user or not verify_password(credentials.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(db_user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserRead(
            id=db_user.id,
            email=db_user.email,
            name=db_user.name,
            created_at=db_user.created_at
        )
    )

@app.get("/api/auth/me", response_model=UserRead)
def get_current_user_info(user_id: UUID = Depends(get_current_user_from_header), db: Session = Depends(get_session)):
    user = crud.get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at
    )

@app.post("/api/auth/signout")
def signout():
    # In a JWT-based system, the token is stateless and cannot be invalidated server-side
    # The frontend should clear the token from local storage/session storage
    # This endpoint can be used to perform any server-side cleanup if needed
    return {"status": "success", "message": "Signed out successfully"}

# Task Endpoints
@app.post("/api/tasks/", response_model=TaskRead)
def create_task(task: TaskCreate, user_id: UUID = Depends(get_current_user_from_header), db: Session = Depends(get_session)):
    return crud.create_task(db=db, task=task, user_id=user_id)

@app.get("/api/tasks/", response_model=TaskListResponse)
def read_tasks(
    status: str = "all",
    sort: str = "created",
    skip: int = 0,
    limit: int = 100,
    user_id: UUID = Depends(get_current_user_from_header),
    db: Session = Depends(get_session)
):
    tasks = crud.get_tasks(db, user_id=user_id, status=status, sort=sort, skip=skip, limit=limit)
    total = crud.get_tasks_count(db, user_id=user_id, status=status)
    return TaskListResponse(items=tasks, total=total, limit=limit, offset=skip)

@app.get("/api/tasks/{task_id}", response_model=TaskRead)
def read_task(task_id: int, user_id: UUID = Depends(get_current_user_from_header), db: Session = Depends(get_session)):
    db_task = crud.get_task(db, task_id=task_id, user_id=user_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@app.put("/api/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, task: TaskUpdate, user_id: UUID = Depends(get_current_user_from_header), db: Session = Depends(get_session)):
    db_task = crud.update_task(db, task_id=task_id, task_in=task, user_id=user_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@app.delete("/api/tasks/{task_id}", response_model=TaskRead)
def delete_task(task_id: int, user_id: UUID = Depends(get_current_user_from_header), db: Session = Depends(get_session)):
    db_task = crud.delete_task(db, task_id=task_id, user_id=user_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@app.patch("/api/tasks/{task_id}/complete", response_model=TaskRead)
def mark_task_complete(task_id: int, user_id: UUID = Depends(get_current_user_from_header), db: Session = Depends(get_session)):
    task = TaskUpdate(completed=True)
    db_task = crud.update_task(db, task_id=task_id, task_in=task, user_id=user_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

# Health check endpoint
@app.get("/api/health")
def health_check():
    return {"status": "ok"}
