from fastapi import APIRouter, HTTPException
import logging
from schemas import TaskCreate
from services.project_service import ProjectService

router = APIRouter(
    prefix="/api/tasks",
    tags=["tasks"]
)

logger = logging.getLogger(__name__)
project_service = ProjectService()


@router.post("/create")
async def create_task(task_data: TaskCreate):
    """Create a new task for a project"""
    try:
        task = project_service.create_task(task_data)
        logger.info(f"✅ Task created via API: {task.id}")
        
        return {
            "status": "success",
            "task_id": task.id,
            "title": task.title,
            "description": task.description,
            "project_id": task.project_id,
            "priority": task.priority,
            "status": task.status,
            "deadline": task.deadline,
            "requirements": task.requirements,
            "created_at": task.created_at
        }
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("")
async def list_tasks(
    skip: int = 0,
    limit: int = 20,
    project_id: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assigned_user_id: str | None = None,
):
    """
    List tasks with pagination and optional filters:
      - project_id
      - status
      - priority
      - assigned_user_id (filters tasks that have an assignment for this user)
    """
    try:
        tasks = project_service.list_tasks(skip=skip, limit=limit)

        # Apply simple in-memory filters
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]
        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        if assigned_user_id:
            # get assignments for the user (use a large limit to be safe)
            assignments = project_service.list_assignments(skip=0, limit=10000, user_id=assigned_user_id)
            task_ids_for_user = {a.task_id for a in assignments}
            tasks = [t for t in tasks if t.id in task_ids_for_user]

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
                    "requirements": task.requirements or [],
                    "assignments_count": len(project_service.get_task_assignments(task.id)),
                    "created_at": task.created_at,
                    "updated_at": task.updated_at
                } for task in tasks
            ]
        }
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{task_id}")
async def get_task(task_id: str, detailed: bool = False):
    """Get task by ID, optionally with details"""
    try:
        if detailed:
            task_data = project_service.get_task_with_details(task_id)
            if not task_data:
                raise HTTPException(status_code=404, detail="Task not found")
            return {
                "status": "success",
                "task": task_data
            }
        else:
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
                    "requirements": task.requirements or [],
                    "created_at": task.created_at,
                    "updated_at": task.updated_at
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{task_id}/comments")
async def get_task_comments(task_id: str):
    """Get all comments for a task"""
    try:
        # Verify task exists
        task = project_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        comments = project_service.get_task_comments(task_id)
        
        return {
            "status": "success",
            "task_id": task_id,
            "count": len(comments),
            "comments": [
                {
                    "id": comment.id,
                    "user_id": comment.user_id,
                    "content": comment.content,
                    "created_at": comment.created_at,
                    "updated_at": comment.updated_at
                } for comment in comments
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting task comments: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
