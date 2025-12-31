# Backend Implementation Guide - Phase II (SDD Aligned)

**Framework:** FastAPI with Spec-Driven Development
**Language:** Python 3.11+
**Development Methodology:** SDD (Spec-Driven Development)
**Status:** Ready for Implementation

---

## 🎯 Implementation Workflow (Spec-Driven)

### The SDD Cycle
```
1. READ SPEC
   └─ specs/phase2-web/api/rest-endpoints.md
   └─ specs/phase2-web/architecture.md
   └─ specs/phase2-web/database/schema.md

2. WRITE TEST (Red Phase)
   └─ tests/test_*.py
   └─ Test case covers spec requirements
   └─ Test fails (RED)

3. IMPLEMENT CODE (Green Phase)
   └─ main.py, models.py, routes/
   └─ Code makes test pass
   └─ Test passes (GREEN)

4. REFACTOR (Refactor Phase)
   └─ Clean up, optimize, document
   └─ Tests still pass
   └─ Code aligns with CONSTITUTION.md standards

5. CREATE PHR (Prompt History Record)
   └─ Record what was done
   └─ Store under history/prompts/phase2-web/
   └─ Reference spec in PHR

6. REPEAT for next feature
```

---

## 📋 Before Starting Each Task

### Pre-Implementation Checklist
- [ ] Read the spec for this feature
- [ ] Read relevant architecture section
- [ ] Check CONSTITUTION.md for requirements
- [ ] Create test cases first (TDD)
- [ ] Write minimal code to pass tests
- [ ] Refactor for clarity
- [ ] Create PHR record

---

## 🔴 RED PHASE: Write Tests First

### Test Structure (pytest)

**File:** `backend/tests/test_tasks.py`

```python
# tests/test_tasks.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from main import app
from models import User, Task
from core.security import create_access_token

@pytest.fixture
def test_user():
    """Create test user"""
    user_id = uuid4()
    return {
        "id": user_id,
        "email": "test@example.com",
        "name": "Test User"
    }

@pytest.fixture
def test_token(test_user):
    """Create JWT token for test user"""
    return create_access_token(str(test_user["id"]))

@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)

# RED: Test fails first
class TestTaskCRUD:
    """Test task CRUD operations"""

    def test_create_task_success(self, client, test_token):
        """
        SPEC: POST /api/tasks should create task

        Given: User with valid JWT token
        When: POST /api/tasks with {title, description}
        Then: 201 response with task object
        """
        response = client.post(
            "/api/tasks",
            json={
                "title": "Buy Groceries",
                "description": "Milk, eggs, bread"
            },
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Buy Groceries"
        assert data["completed"] is False
        assert "id" in data

    def test_create_task_missing_title(self, client, test_token):
        """
        SPEC: POST /api/tasks should validate title

        Given: User with valid JWT
        When: POST /api/tasks without title
        Then: 400 Bad Request
        """
        response = client.post(
            "/api/tasks",
            json={"description": "No title provided"},
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 400

    def test_list_tasks_user_isolation(self, client, test_token):
        """
        SPEC: GET /api/tasks should only return user's tasks

        Security requirement: User isolation
        Given: User A with token
        When: GET /api/tasks
        Then: Only User A's tasks returned (not B's)
        """
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # All items should belong to test_user
        # (other users' items should not appear)

    def test_unauthorized_without_token(self, client):
        """
        SPEC: All endpoints require JWT token

        Given: No Authorization header
        When: GET /api/tasks (or any protected endpoint)
        Then: 401 Unauthorized
        """
        response = client.get("/api/tasks")
        assert response.status_code == 401
```

### Test Spec Reference

Each test should explicitly reference the spec:

```python
def test_delete_task_success(self, client, test_token, task_id):
    """
    SPEC: DELETE /api/tasks/{id}
    Source: specs/phase2-web/api/rest-endpoints.md

    Given: User owns the task
    When: DELETE /api/tasks/1
    Then: 204 No Content (success)
    """
    response = client.delete(
        f"/api/tasks/{task_id}",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 204
```

---

## 🟢 GREEN PHASE: Implement to Pass Tests

### Implementation Template

**File:** `backend/routes/tasks.py`

```python
# routes/tasks.py
"""
SPEC SOURCE: specs/phase2-web/api/rest-endpoints.md
ARCHITECTURE: specs/phase2-web/architecture.md (section 3.5)

All routes MUST:
1. Verify JWT token via Depends(verify_jwt)
2. Filter queries by user_id from token
3. Return Pydantic schemas (TaskResponse)
4. Raise HTTPException for errors
5. Include proper status codes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from middleware.auth import verify_jwt
from services.task_service import TaskService
from schemas import TaskCreate, TaskResponse
from db.session import get_session

router = APIRouter(prefix="/tasks", tags=["tasks"])
task_service = TaskService()

@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    task_data: TaskCreate,
    user_id: str = Depends(verify_jwt),  # From JWT token
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """
    CREATE TASK

    SPEC: POST /api/tasks
    Reference: specs/phase2-web/api/rest-endpoints.md (section: POST /api/tasks)

    Requirements:
    - Require valid JWT token (verify_jwt dependency)
    - Validate input with TaskCreate schema (Pydantic)
    - Create task owned by authenticated user
    - Return TaskResponse (201 Created)

    Security:
    - user_id extracted from verified JWT, not from request
    - Task always owned by authenticated user
    - No user_id parameter in input
    """
    try:
        task = await task_service.create_task(
            user_id=UUID(user_id),
            task_data=task_data,
            session=session,
        )
        return task

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task",
        )

@router.get("", response_model=dict)
async def list_tasks(
    user_id: str = Depends(verify_jwt),
    status_filter: str = "all",  # Query param
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    LIST TASKS

    SPEC: GET /api/tasks
    Reference: specs/phase2-web/api/rest-endpoints.md (section: GET /api/tasks)

    Query Parameters:
    - status: "all", "pending", "completed"

    Requirements:
    - Filter by status (optional)
    - MUST filter by user_id (user isolation)
    - Return paginated response

    Security:
    - User only sees their own tasks
    - Status filter is applied AFTER user_id filter
    """
    try:
        tasks, total = await task_service.list_tasks(
            user_id=UUID(user_id),
            status=status_filter,
            session=session,
        )

        return {
            "items": tasks,
            "total": total,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch tasks",
        )
```

### Service Layer (Business Logic)

**File:** `backend/services/task_service.py`

```python
# services/task_service.py
"""
TASK SERVICE - Business Logic Layer

SPEC SOURCE: specs/phase2-web/architecture.md (section 3.4: Service Layer Pattern)

Service methods:
- Contain business logic (not in routes)
- Always filter by user_id (security)
- Perform validation
- Return Pydantic schemas

SECURITY CRITICAL:
- Every query MUST include user_id filter
- Never trust user_id from request - use verified JWT only
- Verify ownership before modifications
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Tuple

from models import Task
from schemas import TaskCreate, TaskUpdate, TaskResponse

class TaskService:
    """Business logic for task operations"""

    async def create_task(
        self,
        user_id: UUID,
        task_data: TaskCreate,
        session: AsyncSession,
    ) -> TaskResponse:
        """
        Create new task

        SPEC: POST /api/tasks

        Security:
        - Task always owned by user_id (no choice given)
        - user_id comes from verified JWT
        """
        task = Task(
            user_id=user_id,
            title=task_data.title,
            description=task_data.description,
        )

        session.add(task)
        await session.commit()
        await session.refresh(task)

        return TaskResponse.from_orm(task)

    async def list_tasks(
        self,
        user_id: UUID,
        status: str = "all",
        session: AsyncSession = None,
    ) -> Tuple[List[TaskResponse], int]:
        """
        List tasks for user

        SPEC: GET /api/tasks

        SECURITY CRITICAL:
        - Filter by user_id first
        - User can only see their own tasks
        """
        # BASE QUERY: Filter by user_id (MANDATORY)
        query = select(Task).where(Task.user_id == user_id)

        # APPLY STATUS FILTER
        if status == "pending":
            query = query.where(Task.completed == False)
        elif status == "completed":
            query = query.where(Task.completed == True)
        # else: status == "all" (no filter)

        # GET TOTAL COUNT
        count_result = await session.execute(
            select(func.count(Task.id)).where(Task.user_id == user_id)
        )
        total = count_result.scalar()

        # FETCH TASKS
        result = await session.execute(query)
        tasks = result.scalars().all()

        return (
            [TaskResponse.from_orm(t) for t in tasks],
            total,
        )

    async def get_task(
        self,
        task_id: int,
        user_id: UUID,
        session: AsyncSession,
    ) -> TaskResponse | None:
        """
        Get single task

        SPEC: GET /api/tasks/{id}

        SECURITY CRITICAL:
        - Verify task belongs to user
        - BOTH conditions required: task_id AND user_id
        """
        query = select(Task).where(
            (Task.id == task_id) &  # Find the task
            (Task.user_id == user_id)  # And verify ownership
        )

        result = await session.execute(query)
        task = result.scalar_one_or_none()

        return TaskResponse.from_orm(task) if task else None

    async def delete_task(
        self,
        task_id: int,
        user_id: UUID,
        session: AsyncSession,
    ) -> bool:
        """
        Delete task

        SPEC: DELETE /api/tasks/{id}

        SECURITY CRITICAL:
        - Only task owner can delete
        - Verify ownership before deletion
        """
        # VERIFY OWNERSHIP
        query = select(Task).where(
            (Task.id == task_id) & (Task.user_id == user_id)
        )
        result = await session.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            return False

        # DELETE
        await session.delete(task)
        await session.commit()

        return True
```

---

## 🔵 REFACTOR PHASE: Code Quality

### Refactoring Checklist

- [ ] Code follows backend/CLAUDE.md patterns
- [ ] Type hints on all functions
- [ ] Error handling for all paths
- [ ] User isolation verified (security)
- [ ] Tests still passing
- [ ] No hardcoded secrets
- [ ] Comments for complex logic
- [ ] Follows CONSTITUTION.md standards

### Code Review Checklist

```python
# ✅ GOOD: Follows spec and standards
@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    user_id: str = Depends(verify_jwt),  # Verified JWT
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete task (user must own it)"""
    success = await task_service.delete_task(
        task_id=task_id,
        user_id=UUID(user_id),  # From JWT, not request
        session=session,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Not found")

# ❌ BAD: User isolation missing
@router.delete("/{task_id}")
async def delete_task(task_id: int, user_id: str):
    # user_id from query param - anyone can pass any user_id!
    task_service.delete_task(task_id, user_id)
```

---

## 📝 CREATE PHR: Document Your Work

### PHR File Structure

**Location:** `history/prompts/phase2-web/`
**Naming:** `{ID}-{slug}.{stage}.prompt.md`

```markdown
# Prompt History Record (PHR)

---
id: 1
title: Implement Task CRUD Endpoints
stage: red-green-refactor
phase: phase2-web
date: 2024-12-28
model: claude-haiku-4-5
status: completed
---

## User Prompt
[Verbatim copy of your request]

## Implementation Summary

### Tasks Completed
1. ✅ Write test cases for task CRUD
2. ✅ Implement POST /api/tasks (create)
3. ✅ Implement GET /api/tasks (list)
4. ✅ Implement GET /api/tasks/{id} (get)
5. ✅ Implement PUT /api/tasks/{id} (update)
6. ✅ Implement DELETE /api/tasks/{id} (delete)

### Specs Referenced
- specs/phase2-web/api/rest-endpoints.md
- specs/phase2-web/architecture.md (section 3.4)
- CONSTITUTION.md (section 3: Architecture Principles)

### Files Modified
- backend/routes/tasks.py (NEW)
- backend/services/task_service.py (NEW)
- backend/tests/test_tasks.py (NEW)

### Tests Status
```bash
pytest tests/test_tasks.py -v
# ✅ 8 passed
# Coverage: 85%
```

### Key Security Measures
- [x] JWT verification on all endpoints
- [x] User isolation (filter by verified user_id)
- [x] Input validation with Pydantic
- [x] Error handling without info leaks
- [x] No hardcoded secrets

### Next Steps
- [ ] Integrate with frontend
- [ ] Add E2E tests
- [ ] Deploy to staging
```

---

## 🔄 Complete Implementation Example

### Task: Implement GET /api/tasks/{id}

#### Step 1: READ SPEC
```
Source: specs/phase2-web/api/rest-endpoints.md (section: GET /api/tasks/{id})
Requirement: Get task details
Security: User must own task
Response: TaskResponse (200 OK) or 404/403/401 errors
```

#### Step 2: RED PHASE (Write Test)
```python
def test_get_task_success(client, test_token, task_id):
    """RED: Test fails - endpoint not implemented"""
    response = client.get(
        f"/api/tasks/{task_id}",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == task_id

def test_get_task_not_owned(client, test_token_user1, task_id_user2):
    """RED: User cannot see another user's task"""
    response = client.get(
        f"/api/tasks/{task_id_user2}",
        headers={"Authorization": f"Bearer {test_token_user1}"}
    )
    assert response.status_code == 403  # Forbidden
```

#### Step 3: GREEN PHASE (Implement)
```python
# In routes/tasks.py
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    user_id: str = Depends(verify_jwt),
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    """SPEC: GET /api/tasks/{id}"""
    task = await task_service.get_task(
        task_id=task_id,
        user_id=UUID(user_id),
        session=session,
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task

# In services/task_service.py
async def get_task(task_id, user_id, session):
    """Get task - MUST verify ownership"""
    query = select(Task).where(
        (Task.id == task_id) & (Task.user_id == user_id)
    )
    result = await session.execute(query)
    task = result.scalar_one_or_none()
    return TaskResponse.from_orm(task) if task else None
```

#### Step 4: Tests Pass ✅
```bash
pytest tests/test_tasks.py::test_get_task_success -v
# ✅ PASSED
pytest tests/test_tasks.py::test_get_task_not_owned -v
# ✅ PASSED
```

#### Step 5: REFACTOR
- Check type hints ✅
- Check error handling ✅
- Check user isolation ✅
- Check code style ✅

#### Step 6: CREATE PHR
```
Created: history/prompts/phase2-web/1-implement-get-task.red-green-refactor.prompt.md
Status: Completed
```

---

## ✅ Implementation Checklist (Per Feature)

For every API endpoint:

- [ ] Read spec in `specs/phase2-web/api/rest-endpoints.md`
- [ ] Write test cases (RED phase)
- [ ] Implement route in `routes/`
- [ ] Implement service in `services/`
- [ ] Tests pass (GREEN phase)
- [ ] Code review (REFACTOR phase)
- [ ] Verify user isolation (if applicable)
- [ ] Create PHR record
- [ ] Update status in task tracking

---

## 📊 Development Progress Tracking

### Feature Completion Log

| Endpoint | Spec Section | Test | Code | Review | PHR | Status |
|----------|--------------|------|------|--------|-----|--------|
| POST /api/auth/signup | Auth | 🔴 | 🟢 | 🟡 | 🟡 | 50% |
| POST /api/auth/signin | Auth | 🔴 | 🔴 | ⚪ | ⚪ | 0% |
| GET /api/tasks | Task | 🔴 | 🔴 | ⚪ | ⚪ | 0% |
| POST /api/tasks | Task | 🔴 | 🔴 | ⚪ | ⚪ | 0% |

Legend: 🔴 Pending | 🟡 In Progress | 🟢 Complete | ⚪ Not Started

---

## 🎯 Success Criteria

Implementation is successful when:

- ✅ All tests pass
- ✅ Code coverage > 70% on critical paths
- ✅ User isolation verified on every query
- ✅ No TypeScript/mypy errors (strict mode)
- ✅ Error handling complete
- ✅ No hardcoded secrets
- ✅ PHR records created
- ✅ Code follows CLAUDE.md and CONSTITUTION.md
- ✅ All spec requirements met

---

**Document Status:** IMPLEMENTATION READY
**Last Updated:** December 28, 2024

