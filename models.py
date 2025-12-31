from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from uuid import UUID, uuid4

# User Models
class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    name: Optional[str] = None

class User(UserBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    tasks: list["Task"] = Relationship(back_populates="user")

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: UUID
    created_at: datetime

class UserLogin(SQLModel):
    email: str
    password: str

# Task Models
class TaskBase(SQLModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class Task(TaskBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="tasks")
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

class TaskCreate(TaskBase):
    pass

class TaskRead(TaskBase):
    id: int
    user_id: UUID
    created_at: datetime
    updated_at: datetime

class TaskUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

# Task List Response Model
class TaskListResponse(SQLModel):
    items: List[TaskRead]
    total: int
    limit: int
    offset: int

# Token Models
class TokenResponse(SQLModel):
    access_token: str
    token_type: str
    user: UserRead

class AuthResponse(SQLModel):
    user: UserRead
    token: str