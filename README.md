# API Router Structure - Auto Project Manager

## Project Structure

```
auto-pm/
├── main.py                          # Main FastAPI application
├── routers/                         # API route modules
│   ├── __init__.py
│   ├── users.py                     # User management endpoints
│   ├── projects.py                  # Project management endpoints
│   ├── tasks.py                     # Task management endpoints
│   ├── assignments.py               # Assignment management endpoints
│   ├── comments.py                  # Comment management endpoints
│   ├── task_weights.py              # Task weight management endpoints
│   └── webhooks.py                  # Zalo webhook and integration endpoints
├── services/                        # Business logic services
│   ├── project_service.py          # Database operations
│   ├── zalo_service.py             # Zalo API client (low-level)
│   ├── zalo_webhook_service.py     # Webhook event handler (high-level)
│   └── analysis_cv.py              # CV analysis service
├── schemas.py                       # Pydantic models
├── models.py                        # SQLAlchemy models
└── database.py                      # Database configuration
```

## Router Modules

### 1. **users.py** - User Management
**Prefix:** `/api/users`  
**Tag:** `users`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users/create` | Create a new user |
| GET | `/api/users` | List all users (with pagination) |
| GET | `/api/users/{user_id}` | Get user by ID |

### 2. **projects.py** - Project Management
**Prefix:** `/api/projects`  
**Tag:** `projects`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects/create` | Create a new project |
| GET | `/api/projects` | List all projects (with filters) |
| GET | `/api/projects/{project_id}` | Get project by ID |
| GET | `/api/projects/{project_id}/comments` | Get all comments for a project |

### 3. **tasks.py** - Task Management
**Prefix:** `/api/tasks`  
**Tag:** `tasks`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tasks/create` | Create a new task |
| GET | `/api/tasks` | List all tasks (with filters) |
| GET | `/api/tasks/{task_id}` | Get task by ID |
| GET | `/api/tasks/{task_id}/comments` | Get all comments for a task |

### 4. **assignments.py** - Assignment Management
**Prefix:** `/api/assignments`  
**Tag:** `assignments`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/assignments/assign` | Assign user to task |
| GET | `/api/assignments` | List all assignments (with filters) |
| GET | `/api/assignments/{assignment_id}` | Get assignment by ID |

### 5. **comments.py** - Comment Management
**Prefix:** `/api/comments`  
**Tag:** `comments`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/comments/create` | Create a new comment |
| GET | `/api/comments` | List all comments (with filters) |
| GET | `/api/comments/{comment_id}` | Get comment by ID |
| PUT | `/api/comments/{comment_id}` | Update comment |
| DELETE | `/api/comments/{comment_id}` | Delete comment |

### 6. **task_weights.py** - Task Weight Management
**Prefix:** `/api/task-weights`  
**Tag:** `task-weights`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/task-weights/create` | Create a new task weight |
| GET | `/api/task-weights` | List all task weights |
| GET | `/api/task-weights/{task_weight_id}` | Get task weight by ID |
| GET | `/api/task-weights/by-name/{task_name}` | Get task weight by name |
| PUT | `/api/task-weights/{task_weight_id}` | Update task weight |
| DELETE | `/api/task-weights/{task_weight_id}` | Delete task weight |

### 7. **webhooks.py** - Zalo Integration
**Prefix:** `/api/zalo`  
**Tag:** `zalo`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/zalo/webhook` | Handle Zalo webhook events |
| GET | `/api/zalo/conversation/{zalo_user_id}` | Get conversation history |
| GET | `/api/zalo/pending-registrations` | Get all pending registrations |
| POST | `/api/zalo/approve/{registration_id}` | Approve registration |
| POST | `/api/zalo/decline/{registration_id}` | Decline registration |

## Main Application (main.py)

### Features:
- ✅ Modular router architecture
- ✅ Centralized configuration
- ✅ Database initialization on startup
- ✅ CORS middleware configured
- ✅ Health check endpoint
- ✅ Backward compatibility for old webhook endpoint

### Endpoints in main.py:
```python
GET  /health              # Health check
POST /webhook-zalooa      # Backward compatibility redirect
```

## Service Architecture

### Separation of Concerns:

#### **ZaloService** (Low-level API Client)
- Direct Zalo API calls
- Send messages
- Get conversations
- Download files

#### **ZaloWebhookService** (High-level Business Logic)
- Handle webhook events
- CV registration workflow
- HR approval process
- User notifications

#### **ProjectService** (Database Operations)
- CRUD operations for all entities
- Data validation
- Business rules enforcement

## Benefits of This Structure

### 1. **Modularity**
- Each router handles one domain
- Easy to locate and modify code
- Clear separation of concerns

### 2. **Scalability**
- Add new routers without touching existing code
- Independent testing per module
- Parallel development possible

### 3. **Maintainability**
- Smaller, focused files
- Clear naming conventions
- Easy to understand flow

### 4. **Testability**
- Mock individual routers
- Unit test each module separately
- Integration tests per domain

### 5. **Documentation**
- Auto-generated OpenAPI docs organized by tags
- Clear API grouping in Swagger UI
- Easy to navigate API structure

## How to Add a New Router

1. Create new file in `routers/` directory:
```python
# routers/new_feature.py
from fastapi import APIRouter, HTTPException
import logging

router = APIRouter(
    prefix="/api/new-feature",
    tags=["new-feature"]
)

logger = logging.getLogger(__name__)

@router.get("/")
async def list_items():
    return {"items": []}
```

2. Import and register in `main.py`:
```python
from routers import new_feature

app.include_router(new_feature.router)
```

## Migration Notes

### Changed Endpoints:
- `/webhook-zalooa` → `/api/zalo/webhook` (old endpoint still works for backward compatibility)
- `/api/get_conversation/{zalo_user_id}` → `/api/zalo/conversation/{zalo_user_id}`

### All other endpoints remain the same! ✅

## Running the Application

```bash
# Development
uvicorn main:app --reload --host 0.0.0.0 --port 5544

# Production
uvicorn main:app --host 0.0.0.0 --port 5544 --workers 4
```

## API Documentation

Once running, access:
- **Swagger UI**: http://localhost:5544/docs
- **ReDoc**: http://localhost:5544/redoc
- **OpenAPI JSON**: http://localhost:5544/openapi.json

## Best Practices Implemented

✅ **Router separation by domain**  
✅ **Consistent naming conventions**  
✅ **Proper error handling**  
✅ **Logging throughout**  
✅ **Type hints everywhere**  
✅ **Docstrings for all endpoints**  
✅ **Validation with Pydantic**  
✅ **Service layer pattern**  
✅ **Dependency injection ready**  

## Next Steps for Further Improvement

1. **Dependency Injection**: Replace global `project_service` instances with FastAPI dependencies
2. **Database Sessions**: Use FastAPI dependency for database session management
3. **Authentication**: Add JWT authentication middleware
4. **Rate Limiting**: Implement rate limiting per endpoint
5. **Caching**: Add Redis caching for frequently accessed data
6. **Testing**: Create pytest test suite for each router
7. **CI/CD**: Set up GitHub Actions for automated testing and deployment
