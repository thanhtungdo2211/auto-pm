from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Optional, Any, Dict
from datetime import datetime
from enum import Enum

# ============ Request Schemas ============
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None  # Made optional for Zalo users
    phone: Optional[str] = None
    cv: Optional[str] = None
    cv_data: Optional[Dict[str, Any]] = None
    zalo_user_id: Optional[str] = None
    description: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None
    skills: Optional[List[str]] = []
    role: Optional[str] = "staff"
    is_active: Optional[bool] = True
    
    @field_validator('email', 'zalo_user_id')
    @classmethod
    def validate_identifier(cls, v, info):
        """At least one of email or zalo_user_id must be provided"""
        if info.field_name == 'email':
            return v
        # Check if at least one identifier exists
        if not v and not info.data.get('email'):
            raise ValueError('Either email or zalo_user_id must be provided')
        return v
    
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

class TaskUpdate(BaseModel):
    """Schema for updating a task - all fields are optional"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|cancelled)$")
    deadline: Optional[datetime] = None
    complete_at: Optional[datetime] = None
    requirements: Optional[List[str]] = None
    additional_info: Optional[Dict[str, Any]] = None
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v is not None and v not in ['low', 'medium', 'high', 'urgent']:
            raise ValueError('Priority must be one of: low, medium, high, urgent')
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in ['pending', 'in_progress', 'completed', 'cancelled']:
            raise ValueError('Status must be one of: pending, in_progress, completed, cancelled')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Task Title",
                "description": "Updated description",
                "priority": "high",
                "status": "in_progress",
                "deadline": "2024-12-31T23:59:59"
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


class TaskWeightCreate(BaseModel):
    task_name: str = Field(..., min_length=1, max_length=255)
    weight: Dict[str, float] = Field(
        ..., 
        description="Weight by experience level (e.g., {'senior': 1.0, 'middle': 0.5, 'junior': 0.3})"
    )
    
    @field_validator('weight')
    @classmethod
    def validate_weight(cls, v):
        """Validate weight values are between 0 and 1"""
        if not v:
            raise ValueError("Weight cannot be empty")
        
        for level, weight_value in v.items():
            if not isinstance(weight_value, (int, float)):
                raise ValueError(f"Weight value for '{level}' must be a number")
            if weight_value < 0 or weight_value > 1:
                raise ValueError(f"Weight value for '{level}' must be between 0 and 1")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_name": "Backend Development",
                "weight": {
                    "senior": 1.0,
                    "middle": 0.6,
                    "junior": 0.3
                }
            }
        }


class TaskWeightUpdate(BaseModel):
    task_name: Optional[str] = Field(None, min_length=1, max_length=255)
    weight: Optional[Dict[str, float]] = Field(
        None,
        description="Weight by experience level"
    )
    
    @field_validator('weight')
    @classmethod
    def validate_weight(cls, v):
        """Validate weight values are between 0 and 1"""
        if v is None:
            return v
            
        if not v:
            raise ValueError("Weight cannot be empty")
        
        for level, weight_value in v.items():
            if not isinstance(weight_value, (int, float)):
                raise ValueError(f"Weight value for '{level}' must be a number")
            if weight_value < 0 or weight_value > 1:
                raise ValueError(f"Weight value for '{level}' must be between 0 and 1")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_name": "Backend Development",
                "weight": {
                    "senior": 1.0,
                    "middle": 0.7,
                    "junior": 0.4
                }
            }
        }


class TaskWeightResponse(BaseModel):
    id: str
    task_name: str
    weight: Dict[str, float]  # Changed from int to Dict
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


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