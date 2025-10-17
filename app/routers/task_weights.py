from fastapi import APIRouter, HTTPException
import logging
from app.schemas import TaskWeightCreate, TaskWeightUpdate
from services.project_service import ProjectService

router = APIRouter(
    prefix="/api/task-weights",
    tags=["task-weights"]
)

logger = logging.getLogger(__name__)
project_service = ProjectService()


@router.post("/create")
async def create_task_weight(task_weight_data: TaskWeightCreate):
    """Create a new task weight"""
    try:
        task_weight = project_service.create_task_weight(task_weight_data)
        logger.info(f"✅ Task weight created via API: {task_weight.id}")
        
        return {
            "status": "success",
            "task_weight_id": task_weight.id,
            "task_name": task_weight.task_name,
            "weight": task_weight.weight,
            "created_at": task_weight.created_at
        }
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error creating task weight: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("")
async def list_task_weights(skip: int = 0, limit: int = 50):
    """List all task weights"""
    try:
        task_weights = project_service.list_task_weights(skip, limit)
        
        return {
            "status": "success",
            "count": len(task_weights),
            "task_weights": [
                {
                    "id": tw.id,
                    "task_name": tw.task_name,
                    "weight": tw.weight,
                    "created_at": tw.created_at,
                    "updated_at": tw.updated_at
                } for tw in task_weights
            ]
        }
    except Exception as e:
        logger.error(f"❌ Error listing task weights: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{task_weight_id}")
async def get_task_weight(task_weight_id: str):
    """Get task weight by ID"""
    try:
        task_weight = project_service.get_task_weight(task_weight_id)
        if not task_weight:
            raise HTTPException(status_code=404, detail="Task weight not found")
        
        return {
            "status": "success",
            "task_weight": {
                "id": task_weight.id,
                "task_name": task_weight.task_name,
                "weight": task_weight.weight,
                "created_at": task_weight.created_at,
                "updated_at": task_weight.updated_at
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting task weight: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/by-name/{task_name}")
async def get_task_weight_by_name(task_name: str):
    """Get task weight by task name"""
    try:
        task_weight = project_service.get_task_weight_by_name(task_name)
        if not task_weight:
            raise HTTPException(status_code=404, detail="Task weight not found")
        
        return {
            "status": "success",
            "task_weight": {
                "id": task_weight.id,
                "task_name": task_weight.task_name,
                "weight": task_weight.weight,
                "created_at": task_weight.created_at,
                "updated_at": task_weight.updated_at
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting task weight by name: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{task_weight_id}")
async def update_task_weight(task_weight_id: str, update_data: TaskWeightUpdate):
    """Update task weight"""
    try:
        update_dict = update_data.model_dump(exclude_none=True)
        if not update_dict:
            raise ValueError("No fields to update")
        
        task_weight = project_service.update_task_weight(task_weight_id, **update_dict)
        logger.info(f"✅ Task weight updated via API: {task_weight_id}")
        
        return {
            "status": "success",
            "task_weight_id": task_weight.id,
            "task_name": task_weight.task_name,
            "weight": task_weight.weight,
            "updated_at": task_weight.updated_at
        }
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error updating task weight: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{task_weight_id}")
async def delete_task_weight(task_weight_id: str):
    """Delete a task weight"""
    try:
        project_service.delete_task_weight(task_weight_id)
        logger.info(f"✅ Task weight deleted via API: {task_weight_id}")
        
        return {
            "status": "success",
            "message": "Task weight deleted successfully"
        }
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error deleting task weight: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
