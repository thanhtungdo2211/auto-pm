from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime
import qrcode
import io
import os

from database import init_db, get_db
from schemas import (
    UserCreate, ProjectCreate, TaskCreate, 
    AssignmentRequest, AgentResponse
)
from services.agent_service import AgentService
from services.zalo_service import ZaloService
from services.project_service import ProjectService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
agent_service = AgentService()
zalo_service = ZaloService()
project_service = ProjectService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    init_db()
    logger.info("Application started")
    yield
    # Shutdown
    logger.info("Application shutdown")

app = FastAPI(
    title="Auto Project Manager API",
    description="Automated project management with AI agents",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# API Endpoints
# ============================================

@app.post("/api/users/create")
async def create_user(user_data: UserCreate):
    """
    Create a new valid user with CV and description
    """
    try:
        user = project_service.create_user(user_data)
        logger.info(f"User created: {user.id}")
        
        return {
            "status": "success",
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/users")
async def list_users(skip: int = 0, limit: int = 20):
    users = project_service.list_users(skip, limit)
    return {
        "status": "success",
        "count": len(users),
        "users": [
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "skills": user.skills,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            } for user in users
        ]
    }
    
@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    user = project_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "status": "success",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "skills": user.skills,
            "cv": user.cv,
            "description": user.description,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
    }


@app.post("/api/projects/create")
async def create_project(project_data: ProjectCreate):
    """
    Create a new project
    """
    try:
        project = project_service.create_project(project_data)
        logger.info(f"Project created: {project.id}")
        
        return {
            "status": "success",
            "project_id": project.id,
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/projects")
async def list_projects(skip: int = 0, limit: int = 20):
    projects = project_service.list_projects(skip, limit)
    return {
        "status": "success",
        "count": len(projects),
        "projects": [
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "manager_id": project.manager_id,
                "status": project.status,
                "created_at": project.created_at,
                "updated_at": project.updated_at
            } for project in projects
        ]
    }

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "status": "success",
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "manager_id": project.manager_id,
            "status": project.status,
            "created_at": project.created_at,
            "updated_at": project.updated_at
        }
    }

@app.post("/api/tasks/create")
async def create_task(task_data: TaskCreate):
    """
    Create a new task for a project
    """
    try:
        task = project_service.create_task(task_data)
        logger.info(f"Task created: {task.id}")
        
        # Send task info to Agent (Assign Task Agent)
        # agent_response = await agent_service.send_to_assign_agent(task)
        
        return {
            "status": "success",
            "task_id": task.id,
            "title": task.title,
            "project_id": task.project_id,
            # "agent_response": agent_response.dict() if agent_response else None,
            "created_at": task.created_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/tasks")
async def list_tasks(skip: int = 0, limit: int = 20, project_id: str | None = None):
    if project_id:
        tasks = project_service.get_project_tasks(project_id)
    else:
        tasks = project_service.list_tasks(skip, limit)
    return {
        "status": "success",
        "count": len(tasks),
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "project_id": task.project_id,
                "priority": task.priority,
                "status": task.status,
                "deadline": task.deadline,
                "requirements": task.requirements,
                "created_at": task.created_at,
                "updated_at": task.updated_at
            } for task in tasks
        ]
    }

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    task = project_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "status": "success",
        "task": {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "project_id": task.project_id,
            "priority": task.priority,
            "status": task.status,
            "deadline": task.deadline,
            "requirements": task.requirements,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
    }

@app.post("/api/assignments/assign")
async def assign_member(assignment_data: AssignmentRequest):
    """
    Assign members to tasks and generate Zalo OA link
    """
    try:
        # Validate data
        user = project_service.get_user(assignment_data.user_id)
        task = project_service.get_task(assignment_data.task_id)
        project = project_service.get_project(task.project_id)
        
        if not user or not task or not project:
            raise ValueError("Invalid user, task, or project")
        
        # Create assignment
        assignment = project_service.create_assignment(
            user_id=assignment_data.user_id,
            task_id=assignment_data.task_id,
            project_id=task.project_id
        )
        
        # Prepare comprehensive info for Agent
        # agent_payload = {
        #     "assignment_id": assignment.id,
        #     "user": {
        #         "id": user.id,
        #         "name": user.name,
        #         "email": user.email,
        #         "cv": user.cv,
        #         "description": user.description,
        #         "skills": user.skills
        #     },
        #     "task": {
        #         "id": task.id,
        #         "title": task.title,
        #         "description": task.description,
        #         "priority": task.priority,
        #         "deadline": task.deadline.isoformat() if task.deadline else None
        #     },
        #     "project": {
        #         "id": project.id,
        #         "name": project.name,
        #         "description": project.description
        #     }
        # }
        
        # # Send to Agent for task exchange and optimization
        # agent_response = await agent_service.send_to_exchange_agent(agent_payload)
        
        # # Generate Zalo OA link/QR code
        # zalo_link = await zalo_service.generate_zalo_oa_link(
        #     user_id=user.id,
        #     assignment_id=assignment.id,
        #     task_id=task.id
        # )
        
        # # Generate QR code
        # qr_code_path = generate_qr_code(zalo_link)
        
        # logger.info(f"Assignment created and Zalo link generated: {assignment.id}")
        
        return {
            "status": "success",
            "assignment_id": assignment.id,
            "user_id": user.id,
            "task_id": task.id,
            "project_id": project.id,
            # "zalo_link": zalo_link,
            # "qr_code_path": qr_code_path,
            # "agent_analysis": agent_response.dict() if agent_response else None,
            "created_at": assignment.created_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error assigning member: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/assignments")
async def list_assignments(
    skip: int = 0,
    limit: int = 20,
    user_id: str | None = None,
    project_id: str | None = None,
    task_id: str | None = None
):
    assignments = project_service.list_assignments(
        skip=skip,
        limit=limit,
        user_id=user_id,
        project_id=project_id,
        task_id=task_id
    )
    return {
        "status": "success",
        "count": len(assignments),
        "assignments": [
            {
                "id": assignment.id,
                "user_id": assignment.user_id,
                "task_id": assignment.task_id,
                "project_id": assignment.project_id,
                "status": assignment.status,
                "zalo_link": assignment.zalo_link,
                "agent_notes": assignment.agent_notes,
                "created_at": assignment.created_at,
                "updated_at": assignment.updated_at
            } for assignment in assignments
        ]
    }

@app.get("/api/assignments/{assignment_id}")
async def get_assignment(assignment_id: str):
    """
    Get assignment details
    """
    try:
        assignment = project_service.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        return {
            "status": "success",
            "assignment_id": assignment.id,
            "user_id": assignment.user_id,
            "task_id": assignment.task_id,
            "project_id": assignment.project_id,
            "zalo_link": assignment.zalo_link,
            "status": assignment.status,
            "created_at": assignment.created_at
        }
    except Exception as e:
        logger.error(f"Error retrieving assignment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/qrcode/{assignment_id}")
async def get_qr_code(assignment_id: str):
    """
    Get QR code for an assignment
    """
    try:
        assignment = project_service.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        qr_code_path = generate_qr_code(assignment.zalo_link)
        return FileResponse(qr_code_path, media_type="image/png")
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "timestamp": datetime.now()}


# ============================================
# Helper Functions
# ============================================

def generate_qr_code(data: str, filename: str = None) -> str:
    """
    Generate QR code from data
    """
    if filename is None:
        filename = f"qrcode_{datetime.now().timestamp()}.png"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Create qrcodes directory if it doesn't exist
    os.makedirs("qrcodes", exist_ok=True)
    
    filepath = f"qrcodes/{filename}"
    img.save(filepath)
    
    return filepath


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)