from fastapi import APIRouter, HTTPException
import logging
from app.schemas import TaskCreate, TaskUpdate
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
            "complete_at": task.complete_at,
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
                    "complete_at": task.complete_at,
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
                    "complete_at": task.complete_at,
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


@router.put("/{task_id}")
async def update_task(task_id: str, task_data: TaskUpdate):
    """
    Update task information
    Only provided fields will be updated
    """
    try:
        # Verify task exists
        task = project_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Build update dict (only include provided fields)
        update_dict = {}
        if task_data.title is not None:
            update_dict["title"] = task_data.title
        if task_data.description is not None:
            update_dict["description"] = task_data.description
        if task_data.priority is not None:
            update_dict["priority"] = task_data.priority
        if task_data.status is not None:
            update_dict["status"] = task_data.status
        if task_data.deadline is not None:
            update_dict["deadline"] = task_data.deadline
        if task_data.complete_at is not None:
            update_dict["complete_at"] = task_data.complete_at
        if task_data.requirements is not None:
            update_dict["requirements"] = task_data.requirements
        if task_data.additional_info is not None:
            update_dict["additional_info"] = task_data.additional_info
        
        # Update task
        updated_task = project_service.update_task(task_id, **update_dict)
        
        logger.info(f"✅ Task updated via API: {task_id}")
        
        return {
            "status": "success",
            "message": "Task updated successfully",
            "task": {
                "id": updated_task.id,
                "title": updated_task.title,
                "description": updated_task.description,
                "project_id": updated_task.project_id,
                "priority": updated_task.priority,
                "status": updated_task.status,
                "deadline": updated_task.deadline,
                "complete_at": updated_task.complete_at,
                "requirements": updated_task.requirements or [],
                "created_at": updated_task.created_at,
                "updated_at": updated_task.updated_at
            }
        }
    
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error updating task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{task_id}/status")
async def update_task_status(task_id: str, status: str):
    """
    Update only the task status
    Valid statuses: pending, in_progress, completed, cancelled
    """
    try:
        # Verify task exists
        task = project_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Validate status
        valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Update status
        updated_task = project_service.update_task_status(task_id, status)
        
        logger.info(f"✅ Task status updated: {task_id} -> {status}")
        
        return {
            "status": "success",
            "message": f"Task status updated to '{status}'",
            "task_id": task_id,
            "new_status": updated_task.status,
            "updated_at": updated_task.updated_at
        }
    
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error updating task status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{task_id}")
async def delete_task(task_id: str, force: bool = False):
    """
    Delete a task
    
    - By default, only tasks with no assignments can be deleted
    - Use force=true to delete task and all its assignments
    """
    try:
        # Verify task exists
        task = project_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Check for assignments
        assignments = project_service.get_task_assignments(task_id)
        
        if assignments and not force:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete task with {len(assignments)} assignment(s). Use force=true to delete anyway."
            )
        
        # Delete task (will cascade delete assignments if force=true)
        success = project_service.delete_task(task_id, force=force)
        
        if success:
            logger.info(f"✅ Task deleted: {task_id} (force={force})")
            return {
                "status": "success",
                "message": "Task deleted successfully",
                "task_id": task_id,
                "assignments_deleted": len(assignments) if force else 0
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete task")
    
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error deleting task: {str(e)}")
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