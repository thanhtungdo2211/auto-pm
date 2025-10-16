from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime, timedelta
from typing import Dict

from database import init_db, get_db
from schemas import (
    UserCreate, ProjectCreate, TaskCreate, 
    AssignmentRequest, AgentResponse
)
from services.agent_service import AgentService
from services.zalo_service import ZaloService
from services.project_service import ProjectService
from services.zalo_webhook_service import ZaloWebhookService
from services.analysis_cv import GenCVAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
agent_service = AgentService()
zalo_service = ZaloService()
cv_analyzer = GenCVAnalyzer()
zalo_webhook_service = ZaloWebhookService(cv_analyzer=cv_analyzer)
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

from typing import Set

# Add cache for processed events
processed_events: Dict[str, datetime] = {}

def cleanup_old_events():
    """Remove events older than 1 hour"""
    cutoff = datetime.now() - timedelta(hours=1)
    to_remove = [
        event_id for event_id, timestamp in processed_events.items()
        if timestamp < cutoff
    ]
    for event_id in to_remove:
        del processed_events[event_id]

@app.post("/webhook-zalooa")
async def zalo_webhook(request: dict):
    try:
        # Cleanup old events
        cleanup_old_events()
        
        # Create idempotency key from request
        event_id = f"{request.get('event_name', '')}_{request.get('timestamp', '')}_{request.get('sender', {}).get('id', '')}"
        
        # Check if already processed
        if event_id in processed_events:
            logger.info(f"Event already processed: {event_id}")
            return {"status": "duplicate", "message": "Event already processed"}
        
        result = await zalo_webhook_service.handle_webhook_event(request)
        
        # Handle CV submission
        if result.get("action") == "cv_received":
            cv_data = result.get("cv_data", {})
            user_id_zalo = result.get("user_id")
            cv_path = result.get("cv_path")
            
            # Store pending registration
            registration_id = zalo_webhook_service.store_pending_registration(
                cv_data=cv_data,
                cv_path=cv_path,
                user_id_zalo=user_id_zalo
            )
            
            # Notify candidate that CV is pending
            await zalo_webhook_service.send_pending_notification(
                user_id_zalo,
                cv_data.get("name", "Unknown")
            )
            
            # Send to HR for approval
            await zalo_webhook_service.notify_hr(registration_id, cv_data)
            
            # Mark event as processed
            processed_events[event_id] = datetime.now()
            
            logger.info(f"✅ CV submitted and pending HR approval: {registration_id}")
            return {
                "status": "success",
                "action": "pending_approval",
                "registration_id": registration_id
            }
        
        # Handle HR approval
        elif result.get("action") == "hr_approved":
            registration_id = result.get("registration_id")
            
            # Get pending registration
            pending = zalo_webhook_service.get_pending_registration(registration_id)
            
            if not pending:
                await zalo_webhook_service.send_zalo_message({
                    "recipient": {"user_id": zalo_webhook_service.hr_user_id},
                    "message": {"text": f"❌ Registration ID không tồn tại: {registration_id}"}
                })
                return {"status": "error", "message": "Registration not found"}
            
            cv_data = pending["cv_data"]
            user_id_zalo = pending["user_id_zalo"]
            
            # Create user with full CV data
            user_create_data = UserCreate(
                name=cv_data.get("name", "Unknown"),
                email=cv_data.get("email"),
                phone=cv_data.get("phone"),
                cv=pending["cv_path"],
                cv_data=cv_data,
                zalo_user_id=user_id_zalo,
                description=cv_data.get("description", ""),
                skills=cv_data.get("skills", []),
                role="staff"
            )
            
            try:
                user = project_service.create_user(user_create_data)
                
                # Remove pending registration
                zalo_webhook_service.remove_pending_registration(registration_id)
                
                # Mark event as processed
                processed_events[event_id] = datetime.now()
                
                # Send approval notification to candidate
                await zalo_webhook_service.send_approval_notification(
                    user_id_zalo,
                    {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "skills": user.skills,
                        "experience_years": cv_data.get("experience_years"),
                        "experience_level": cv_data.get("experience_level")
                    }
                )
                
                # Confirm to HR
                await zalo_webhook_service.send_zalo_message({
                    "recipient": {"user_id": zalo_webhook_service.hr_user_id},
                    "message": {"text": f"✅ Đã tạo tài khoản cho {user.name}\nUser ID: {user.id}"}
                })
                
                logger.info(f"✅ User approved and created: {user.id}")
                return {"status": "success", "user_id": user.id}
                
            except ValueError as e:
                logger.error(f"❌ User creation error: {str(e)}")
                await zalo_webhook_service.send_zalo_message({
                    "recipient": {"user_id": zalo_webhook_service.hr_user_id},
                    "message": {"text": f"❌ Lỗi tạo tài khoản: {str(e)}"}
                })
                return {"status": "error", "message": str(e)}
        
        # Handle HR decline
        elif result.get("action") == "hr_declined":
            registration_id = result.get("registration_id")
            
            # Get pending registration
            pending = zalo_webhook_service.get_pending_registration(registration_id)
            
            if not pending:
                await zalo_webhook_service.send_zalo_message({
                    "recipient": {"user_id": zalo_webhook_service.hr_user_id},
                    "message": {"text": f"❌ Registration ID không tồn tại: {registration_id}"}
                })
                return {"status": "error", "message": "Registration not found"}
            
            cv_data = pending["cv_data"]
            user_id_zalo = pending["user_id_zalo"]
            
            # Remove pending registration
            zalo_webhook_service.remove_pending_registration(registration_id)
            
            # Mark event as processed
            processed_events[event_id] = datetime.now()
            
            # Send rejection notification to candidate
            await zalo_webhook_service.send_rejection_notification(
                user_id_zalo,
                cv_data.get("name", "Unknown")
            )
            
            # Confirm to HR
            await zalo_webhook_service.send_zalo_message({
                "recipient": {"user_id": zalo_webhook_service.hr_user_id},
                "message": {"text": f"✅ Đã từ chối đơn của {cv_data.get('name')}"}
            })
            
            logger.info(f"✅ Registration declined: {registration_id}")
            return {"status": "success", "action": "declined"}
        
        return {"status": "success", "result": result}
    
    except Exception as e:
        logger.error(f"❌ Error processing Zalo webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
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

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "timestamp": datetime.now()}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=5544)