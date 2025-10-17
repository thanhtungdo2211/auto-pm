from fastapi import APIRouter, HTTPException
import logging
from app.schemas import CommentCreate
from services.project_service import ProjectService

router = APIRouter(
    prefix="/api/comments",
    tags=["comments"]
)

logger = logging.getLogger(__name__)
project_service = ProjectService()


@router.post("/create")
async def create_comment(comment_data: CommentCreate):
    """Create a new comment on a task"""
    try:
        comment = project_service.create_comment(comment_data)
        logger.info(f"✅ Comment created via API: {comment.id}")
        
        return {
            "status": "success",
            "comment_id": comment.id,
            "user_id": comment.user_id,
            "task_id": comment.task_id,
            "project_id": comment.project_id,
            "content": comment.content,
            "created_at": comment.created_at
        }
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error creating comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("")
async def list_comments(
    skip: int = 0,
    limit: int = 50,
    user_id: str | None = None,
    project_id: str | None = None,
    task_id: str | None = None
):
    """
    List comments with pagination and optional filters:
      - user_id
      - project_id
      - task_id
    """
    try:
        comments = project_service.list_comments(
            skip=skip,
            limit=limit,
            user_id=user_id,
            project_id=project_id,
            task_id=task_id
        )
        return {
            "status": "success",
            "count": len(comments),
            "comments": [
                {
                    "id": c.id,
                    "user_id": c.user_id,
                    "task_id": c.task_id,
                    "project_id": c.project_id,
                    "content": c.content,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at
                } for c in comments
            ]
        }
    except Exception as e:
        logger.error(f"Error listing comments: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{comment_id}")
async def get_comment(comment_id: str):
    """Get comment by ID"""
    try:
        comment = project_service.get_comment(comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        return {
            "status": "success",
            "comment": {
                "id": comment.id,
                "user_id": comment.user_id,
                "task_id": comment.task_id,
                "project_id": comment.project_id,
                "content": comment.content,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{comment_id}")
async def update_comment(comment_id: str, content: str):
    """Update comment content"""
    try:
        comment = project_service.update_comment(comment_id, content)
        logger.info(f"✅ Comment updated via API: {comment_id}")
        
        return {
            "status": "success",
            "comment_id": comment.id,
            "content": comment.content,
            "updated_at": comment.updated_at
        }
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error updating comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{comment_id}")
async def delete_comment(comment_id: str):
    """Delete a comment"""
    try:
        project_service.delete_comment(comment_id)
        logger.info(f"✅ Comment deleted via API: {comment_id}")
        
        return {
            "status": "success",
            "message": "Comment deleted successfully"
        }
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error deleting comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
