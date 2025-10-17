from fastapi import APIRouter, HTTPException
import logging
from app.schemas import UserCreate
from services.project_service import ProjectService

router = APIRouter(
    prefix="/api/users",
    tags=["users"]
)

logger = logging.getLogger(__name__)
project_service = ProjectService()


@router.post("/create")
async def create_user(user_data: UserCreate):
    """
    Create a new user with CV and description
    Requires either email or zalo_user_id
    """
    try:
        user = project_service.create_user(user_data)
        logger.info(f"✅ User created via API: {user.id}")
        
        return {
            "status": "success",
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "zalo_user_id": user.zalo_user_id,
            "created_at": user.created_at
        }
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("")
async def list_users(skip: int = 0, limit: int = 20):
    """List all users with pagination"""
    try:
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
                    "zalo_user_id": user.zalo_user_id,
                    "role": user.role,
                    "skills": user.skills or [],
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at
                } for user in users
            ]
        }
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}")
async def get_user(user_id: str):
    """Get user details by ID"""
    try:
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
                "zalo_user_id": user.zalo_user_id,
                "role": user.role,
                "skills": user.skills or [],
                "cv": user.cv,
                "cv_data": user.cv_data,
                "description": user.description,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
