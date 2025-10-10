
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    MANAGER = "manager"
    STAFF = "staff"
    ADMIN = "admin"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class AssignmentStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


# ============ Request Schemas ============

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    cv: Optional[str] = None
    description: Optional[str] = None
    skills: Optional[List[str]] = []
    role: Optional[UserRole] = UserRole.STAFF
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Nguyễn Văn A",
                "email": "user@example.com",
                "phone": "+84912345678",
                "cv": "Experience in Python, FastAPI...",
                "description": "5 years backend development",
                "skills": ["Python", "FastAPI", "PostgreSQL"],
                "role": "staff"
            }
        }


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    manager_id: str = Field(..., description="User ID of project manager")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Website Redesign Project",
                "description": "Complete redesign of company website",
                "manager_id": "uuid-of-manager"
            }
        }


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_id: str = Field(..., description="Project ID")
    priority: Optional[TaskPriority] = TaskPriority.MEDIUM
    deadline: Optional[datetime] = None
    requirements: Optional[List[str]] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Design Homepage",
                "description": "Create mockups and design for homepage",
                "project_id": "uuid-of-project",
                "priority": "high",
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


# ============ Response Schemas ============

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str]
    cv: Optional[str]
    description: Optional[str]
    skills: List[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    project_id: str
    priority: TaskPriority
    status: TaskStatus
    deadline: Optional[datetime]
    requirements: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    manager_id: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class AssignmentResponse(BaseModel):
    id: str
    user_id: str
    task_id: str
    project_id: str
    status: AssignmentStatus
    zalo_link: Optional[str]
    zalo_oa_id: Optional[str]
    agent_notes: Optional[Dict[str, Any]]
    created_at: datetime
    
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


# ============================================
# services/project_service.py
# ============================================

from database import SessionLocal, Base
from models import User, Project, Task, Assignment, UserRole, TaskStatus, TaskPriority, AssignmentStatus
from schemas import UserCreate, ProjectCreate, TaskCreate
import logging

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self):
        self.db = SessionLocal()
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError(f"User with email {user_data.email} already exists")
        
        user = User(
            name=user_data.name,
            email=user_data.email,
            phone=user_data.phone,
            cv=user_data.cv,
            description=user_data.description,
            skills=user_data.skills,
            role=user_data.role
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        logger.info(f"User created: {user.id}")
        
        return user
    
    def create_project(self, project_data: ProjectCreate) -> Project:
        """Create a new project"""
        # Verify manager exists
        manager = self.db.query(User).filter(User.id == project_data.manager_id).first()
        if not manager:
            raise ValueError("Manager user not found")
        
        project = Project(
            name=project_data.name,
            description=project_data.description,
            manager_id=project_data.manager_id
        )
        
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        logger.info(f"Project created: {project.id}")
        
        return project
    
    def create_task(self, task_data: TaskCreate) -> Task:
        """Create a new task"""
        # Verify project exists
        project = self.db.query(Project).filter(Project.id == task_data.project_id).first()
        if not project:
            raise ValueError("Project not found")
        
        task = Task(
            title=task_data.title,
            description=task_data.description,
            project_id=task_data.project_id,
            priority=task_data.priority,
            deadline=task_data.deadline,
            requirements=task_data.requirements
        )
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        logger.info(f"Task created: {task.id}")
        
        return task
    
    def create_assignment(self, user_id: str, task_id: str, project_id: str) -> Assignment:
        """Create a new assignment"""
        # Check if assignment already exists
        existing = self.db.query(Assignment).filter(
            Assignment.user_id == user_id,
            Assignment.task_id == task_id
        ).first()
        
        if existing:
            raise ValueError("Assignment already exists for this user and task")
        
        assignment = Assignment(
            user_id=user_id,
            task_id=task_id,
            project_id=project_id
        )
        
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        logger.info(f"Assignment created: {assignment.id}")
        
        return assignment
    
    def get_user(self, user_id: str) -> User:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_project(self, project_id: str) -> Project:
        """Get project by ID"""
        return self.db.query(Project).filter(Project.id == project_id).first()
    
    def get_task(self, task_id: str) -> Task:
        """Get task by ID"""
        return self.db.query(Task).filter(Task.id == task_id).first()
    
    def get_assignment(self, assignment_id: str) -> Assignment:
        """Get assignment by ID"""
        return self.db.query(Assignment).filter(Assignment.id == assignment_id).first()
    
    def update_assignment_status(self, assignment_id: str, status: AssignmentStatus):
        """Update assignment status"""
        assignment = self.db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if assignment:
            assignment.status = status
            self.db.commit()
            self.db.refresh(assignment)
        return assignment