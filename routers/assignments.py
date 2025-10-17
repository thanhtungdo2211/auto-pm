from fastapi import APIRouter, HTTPException
import logging
from schemas import AssignmentRequest
from services.project_service import ProjectService

router = APIRouter(
    prefix="/api/assignments",
    tags=["assignments"]
)

logger = logging.getLogger(__name__)
project_service = ProjectService()


@router.post("/assign")
async def assign_member(assignment_data: AssignmentRequest):
    """Assign a user to a task"""
    try:
        # Validate data
        user = project_service.get_user(assignment_data.user_id)
        task = project_service.get_task(assignment_data.task_id)
        
        if not user:
            raise ValueError(f"User not found: {assignment_data.user_id}")
        if not task:
            raise ValueError(f"Task not found: {assignment_data.task_id}")
        
        project = project_service.get_project(task.project_id)
        if not project:
            raise ValueError(f"Project not found: {task.project_id}")
        
        # Create assignment
        assignment = project_service.create_assignment(
            user_id=assignment_data.user_id,
            task_id=assignment_data.task_id,
            project_id=task.project_id
        )
        
        logger.info(f"✅ Assignment created via API: {assignment.id}")
        
        return {
            "status": "success",
            "assignment_id": assignment.id,
            "user_id": user.id,
            "user_name": user.name,
            "task_id": task.id,
            "task_title": task.title,
            "project_id": project.id,
            "project_name": project.name,
            "created_at": assignment.created_at
        }
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error assigning member: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("")
async def list_assignments(
    skip: int = 0,
    limit: int = 20,
    user_id: str | None = None,
    project_id: str | None = None,
    task_id: str | None = None
):
    """List assignments with pagination and filters"""
    try:
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
    except Exception as e:
        logger.error(f"Error listing assignments: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{assignment_id}")
async def get_assignment(assignment_id: str):
    """Get assignment details"""
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving assignment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
