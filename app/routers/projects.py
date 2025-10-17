from fastapi import APIRouter, HTTPException
import logging
from app.schemas import ProjectCreate
from services.project_service import ProjectService

router = APIRouter(
    prefix="/api/projects",
    tags=["projects"]
)

logger = logging.getLogger(__name__)
project_service = ProjectService()


@router.post("/create")
async def create_project(project_data: ProjectCreate):
    """Create a new project"""
    try:
        project = project_service.create_project(project_data)
        logger.info(f"✅ Project created via API: {project.id}")
        
        return {
            "status": "success",
            "project_id": project.id,
            "name": project.name,
            "description": project.description,
            "manager_id": project.manager_id,
            "status": project.status,
            "created_at": project.created_at
        }
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("")
async def list_projects(
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    manager_id: str | None = None
):
    """List all projects with optional filters"""
    try:
        projects = project_service.list_projects(skip, limit)
        
        # Apply filters
        if status:
            projects = [p for p in projects if p.status == status]
        if manager_id:
            projects = [p for p in projects if p.manager_id == manager_id]
        
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
    except Exception as e:
        logger.error(f"❌ Error listing projects: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{project_id}")
async def get_project(project_id: str, detailed: bool = False):
    """Get project by ID, optionally with details"""
    try:
        if detailed:
            project_data = project_service.get_project_with_details(project_id)
            if not project_data:
                raise HTTPException(status_code=404, detail="Project not found")
            return {
                "status": "success",
                "project": project_data
            }
        else:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{project_id}/comments")
async def get_project_comments(project_id: str):
    """Get all comments for a project"""
    try:
        # Verify project exists
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        comments = project_service.get_project_comments(project_id)
        
        return {
            "status": "success",
            "project_id": project_id,
            "count": len(comments),
            "comments": [
                {
                    "id": comment.id,
                    "user_id": comment.user_id,
                    "task_id": comment.task_id,
                    "content": comment.content,
                    "created_at": comment.created_at,
                    "updated_at": comment.updated_at
                } for comment in comments
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting project comments: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
