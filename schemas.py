from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
from enum import Enum

# ============ Request Schemas ============
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    cv: Optional[str] = None  # File path
    cv_data: Optional[Dict[str, Any]] = None  # Extracted CV data
    zalo_user_id: Optional[str] = None
    description: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None
    skills: Optional[List[str]] = []
    role: Optional[str] = "staff"
    is_active: Optional[bool] = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Nguyễn Văn A",
                "email": "user@example.com",
                "phone": "+84912345678",
                "cv": "/uploads/cvs/user_cv.pdf",
                "cv_data": {
                    "experience_years": 5,
                    "experience_level": "Senior",
                    "projects": []
                },
                "zalo_user_id": "123456789",
                "description": "5 years backend development",
                "skills": ["Python", "FastAPI", "PostgreSQL"],
                "role": "staff"
            }
        }


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    manager_id: str = Field(..., description="User ID of project manager")
    status: Optional[str] = "active"
    additional_info: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Website Redesign Project",
                "description": "Complete redesign of company website",
                "manager_id": "uuid-of-manager",
                "status": "active"
            }
        }


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_id: str = Field(..., description="Project ID")
    priority: Optional[str] = "medium"
    status: Optional[str] = "pending"
    deadline: Optional[datetime] = None
    complete_at: Optional[datetime] = None
    requirements: Optional[List[str]] = []
    additional_info: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Design Homepage",
                "description": "Create mockups and design for homepage",
                "project_id": "uuid-of-project",
                "priority": "high",
                "status": "pending",
                "deadline": "2025-12-31T23:59:59",
                "requirements": ["Figma experience", "UI/UX knowledge"]
            }
        }


class AssignmentRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    task_id: str = Field(..., description="Task ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "uuid-of-user",
                "task_id": "uuid-of-task"
            }
        }


class CommentCreate(BaseModel):
    user_id: str
    task_id: str
    project_id: str
    content: str = Field(..., min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "uuid-of-user",
                "task_id": "uuid-of-task",
                "project_id": "uuid-of-project",
                "content": "This is a comment"
            }
        }


# ============ Response Schemas ============

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str]
    cv: Optional[str]
    cv_data: Optional[Dict[str, Any]]
    zalo_user_id: Optional[str]
    description: Optional[str]
    additional_info: Optional[Dict[str, Any]]
    skills: List[str]
    role: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    project_id: str
    priority: str
    status: str
    deadline: Optional[datetime]
    complete_at: Optional[datetime]
    requirements: List[str]
    additional_info: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    manager_id: str
    status: str
    additional_info: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AssignmentResponse(BaseModel):
    id: str
    user_id: str
    task_id: str
    project_id: str
    status: str
    zalo_link: Optional[str]
    zalo_oa_id: Optional[str]
    agent_notes: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    id: str
    user_id: str
    task_id: str
    project_id: str
    content: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaskWeightResponse(BaseModel):
    id: str
    task_name: str
    weight: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectMemberResponse(BaseModel):
    project_id: str
    user_id: str
    joined_at: datetime
    
    class Config:
        from_attributes = True


# ============ Agent Schemas ============

class AgentResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    agent_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskAssignmentPayload(BaseModel):
    """Payload sent to Assign Task Agent"""
    task_id: str
    title: str
    description: Optional[str]
    priority: str
    requirements: List[str]
    project_name: str
    deadline: Optional[datetime]


class TaskExchangePayload(BaseModel):
    """Payload sent to Task Exchange Agent"""
    assignment_id: str
    user: Dict[str, Any]
    task: Dict[str, Any]
    project: Dict[str, Any]