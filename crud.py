from sqlmodel import Session, select, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from models import Task, TaskCreate, TaskUpdate, User, UserCreate
from security import hash_password

# User CRUD operations
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.exec(select(User).where(User.email == email)).first()

def get_user_by_id(db: Session, user_id: UUID) -> Optional[User]:
    return db.exec(select(User).where(User.id == user_id)).first()

def create_user(db: Session, user: UserCreate) -> User:
    hashed_password = hash_password(user.password)
    db_user = User(
        email=user.email,
        name=user.name,
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Task CRUD operations
def get_task(db: Session, task_id: int, user_id: UUID) -> Optional[Task]:
    return db.exec(select(Task).where(Task.id == task_id).where(Task.user_id == user_id)).first()

def get_tasks_count(db: Session, user_id: UUID, status: str = "all") -> int:
    query = select(func.count(Task.id)).where(Task.user_id == user_id)

    # Apply status filter
    if status == "completed":
        query = query.where(Task.completed == True)
    elif status == "pending":
        query = query.where(Task.completed == False)
    # For "all", no additional filter is needed

    return db.exec(query).one()

def get_tasks(db: Session, user_id: UUID, status: str = "all", sort: str = "created", skip: int = 0, limit: int = 100) -> List[Task]:
    query = select(Task).where(Task.user_id == user_id)

    # Apply status filter
    if status == "completed":
        query = query.where(Task.completed == True)
    elif status == "pending":
        query = query.where(Task.completed == False)
    # For "all", no additional filter is needed

    # Apply sorting
    if sort == "title":
        query = query.order_by(Task.title)
    elif sort == "updated":
        query = query.order_by(Task.updated_at.desc())
    else:  # Default to "created" or any other value
        query = query.order_by(Task.created_at.desc())

    return db.exec(query.offset(skip).limit(limit)).all()

def create_task(db: Session, task: TaskCreate, user_id: UUID) -> Task:
    db_task = Task(**task.dict(), user_id=user_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task(db: Session, task_id: int, task_in: TaskUpdate, user_id: UUID) -> Optional[Task]:
    db_task = get_task(db, task_id, user_id)
    if not db_task:
        return None
    task_data = task_in.dict(exclude_unset=True)
    for key, value in task_data.items():
        setattr(db_task, key, value)
    db_task.updated_at = datetime.utcnow()
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def delete_task(db: Session, task_id: int, user_id: UUID) -> Optional[Task]:
    db_task = get_task(db, task_id, user_id)
    if not db_task:
        return None
    db.delete(db_task)
    db.commit()
    return db_task
