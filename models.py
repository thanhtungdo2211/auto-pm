from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Enum, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    cv = Column(String(500), nullable=True)  # Changed to store file path
    cv_data = Column(JSON, nullable=True)  # Store extracted CV data
    zalo_user_id = Column(String(255), unique=True, nullable=True, index=True)
    description = Column(Text, nullable=True)
    additional_info = Column(JSON, nullable=True)
    skills = Column(JSON, nullable=True, default=[])
    role = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assignments = relationship("Assignment", back_populates="user")
    projects = relationship("Project", secondary="project_members", back_populates="members")


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    manager_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="active", nullable=False)
    additional_info = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    members = relationship("User", secondary="project_members", back_populates="projects")
    assignments = relationship("Assignment", back_populates="project")
    comments = relationship("Comment", back_populates="project")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    priority = Column(String, default="medium", nullable=False)
    status = Column(String, default="pending", nullable=False)
    deadline = Column(DateTime, nullable=True)
    complete_at = Column(DateTime, nullable=True)
    requirements = Column(JSON, nullable=True, default=[])
    additional_info = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignments = relationship("Assignment", back_populates="task", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="task")

class Assignment(Base):
    __tablename__ = "assignments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    status = Column(String, default="pending", nullable=False)
    zalo_link = Column(String(1000), nullable=True)
    zalo_oa_id = Column(String(255), nullable=True)
    agent_notes = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="assignments")
    task = relationship("Task", back_populates="assignments")
    project = relationship("Project", back_populates="assignments")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    task = relationship("Task", back_populates="comments")
    project = relationship("Project", back_populates="comments")

class TaskWeight(Base):
    __tablename__ = "task_weights"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_name = Column(String(255), nullable=False)
    weight = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProjectMember(Base):
    __tablename__ = "project_members"
    
    project_id = Column(String, ForeignKey("projects.id"), primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    joined_at = Column(DateTime, default=datetime.utcnow)