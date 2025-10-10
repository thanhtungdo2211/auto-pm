from database import SessionLocal
from models import (
    User, Project, Task, Assignment, 
    UserRole, TaskStatus, TaskPriority, 
    AssignmentStatus, ProjectMember
)
from schemas import UserCreate, ProjectCreate, TaskCreate
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class ProjectService:
    """Service for managing projects, users, tasks, and assignments"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def __del__(self):
        """Cleanup database session"""
        if hasattr(self, 'db'):
            self.db.close()
    
    # ============================================
    # User Operations
    # ============================================
    
    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user with validation
        
        Args:
            user_data: UserCreate schema with user information
            
        Returns:
            User object
            
        Raises:
            ValueError: If user already exists or validation fails
        """
        try:
            # Check if user already exists
            existing_user = self.db.query(User).filter(
                User.email == user_data.email
            ).first()
            
            if existing_user:
                raise ValueError(f"User with email {user_data.email} already exists")
            
            # Validate email format (basic)
            if "@" not in user_data.email:
                raise ValueError("Invalid email format")
            
            # Create new user
            user = User(
                name=user_data.name,
                email=user_data.email,
                phone=user_data.phone,
                cv=user_data.cv,
                description=user_data.description,
                skills=user_data.skills or [],
                role=user_data.role or UserRole.STAFF,
                is_active=True
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"User created successfully: {user.id} - {user.email}")
            
            return user
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    def get_user(self, user_id: str) -> User:
        """Get user by ID"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User not found: {user_id}")
            return user
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None
    
    def get_user_by_email(self, email: str) -> User:
        """Get user by email"""
        try:
            user = self.db.query(User).filter(User.email == email).first()
            return user
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None
    
    def list_users(self, skip: int = 0, limit: int = 10):
        """List all users with pagination"""
        try:
            users = self.db.query(User).offset(skip).limit(limit).all()
            return users
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return []
    
    def update_user(self, user_id: str, **kwargs) -> User:
        """Update user information"""
        try:
            user = self.get_user(user_id)
            if not user:
                raise ValueError("User not found")
            
            for key, value in kwargs.items():
                if hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            
            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"User updated: {user_id}")
            return user
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user: {str(e)}")
            raise
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete - set is_active to False)"""
        try:
            user = self.get_user(user_id)
            if not user:
                raise ValueError("User not found")
            
            user.is_active = False
            self.db.commit()
            
            logger.info(f"User deleted (deactivated): {user_id}")
            return True
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting user: {str(e)}")
            raise
    
    # ============================================
    # Project Operations
    # ============================================
    
    def create_project(self, project_data: ProjectCreate) -> Project:
        """
        Create a new project
        
        Args:
            project_data: ProjectCreate schema
            
        Returns:
            Project object
            
        Raises:
            ValueError: If manager not found
        """
        try:
            # Verify manager exists
            manager = self.get_user(project_data.manager_id)
            if not manager:
                raise ValueError("Manager user not found")
            
            # Verify manager is actually a manager or admin
            if manager.role not in [UserRole.MANAGER, UserRole.ADMIN]:
                raise ValueError("User must be a manager or admin to create projects")
            
            project = Project(
                name=project_data.name,
                description=project_data.description,
                manager_id=project_data.manager_id,
                status="active"
            )
            
            self.db.add(project)
            self.db.commit()
            self.db.refresh(project)
            
            # Add manager as a member
            self.add_project_member(project.id, project_data.manager_id)
            
            logger.info(f"Project created successfully: {project.id} - {project.name}")
            
            return project
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating project: {str(e)}")
            raise
    
    def get_project(self, project_id: str) -> Project:
        """Get project by ID"""
        try:
            project = self.db.query(Project).filter(
                Project.id == project_id
            ).first()
            if not project:
                logger.warning(f"Project not found: {project_id}")
            return project
        except Exception as e:
            logger.error(f"Error getting project: {str(e)}")
            return None
    
    def list_projects(self, skip: int = 0, limit: int = 10):
        """List all active projects"""
        try:
            projects = self.db.query(Project).filter(
                Project.status == "active"
            ).offset(skip).limit(limit).all()
            return projects
        except Exception as e:
            logger.error(f"Error listing projects: {str(e)}")
            return []
    
    def get_manager_projects(self, manager_id: str):
        """Get all projects managed by a specific user"""
        try:
            projects = self.db.query(Project).filter(
                Project.manager_id == manager_id,
                Project.status == "active"
            ).all()
            return projects
        except Exception as e:
            logger.error(f"Error getting manager projects: {str(e)}")
            return []
    
    def update_project(self, project_id: str, **kwargs) -> Project:
        """Update project information"""
        try:
            project = self.get_project(project_id)
            if not project:
                raise ValueError("Project not found")
            
            for key, value in kwargs.items():
                if hasattr(project, key) and value is not None:
                    setattr(project, key, value)
            
            project.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(project)
            
            logger.info(f"Project updated: {project_id}")
            return project
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating project: {str(e)}")
            raise
    
    def close_project(self, project_id: str) -> Project:
        """Close/deactivate a project"""
        try:
            project = self.get_project(project_id)
            if not project:
                raise ValueError("Project not found")
            
            project.status = "closed"
            self.db.commit()
            self.db.refresh(project)
            
            logger.info(f"Project closed: {project_id}")
            return project
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error closing project: {str(e)}")
            raise
    
    # ============================================
    # Project Member Operations
    # ============================================
    
    def add_project_member(self, project_id: str, user_id: str) -> bool:
        """Add a user as a member to a project"""
        try:
            # Check if already a member
            existing = self.db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            ).first()
            
            if existing:
                logger.warning(f"User {user_id} already a member of project {project_id}")
                return False
            
            member = ProjectMember(
                project_id=project_id,
                user_id=user_id
            )
            
            self.db.add(member)
            self.db.commit()
            
            logger.info(f"User {user_id} added to project {project_id}")
            return True
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding project member: {str(e)}")
            raise
    
    def remove_project_member(self, project_id: str, user_id: str) -> bool:
        """Remove a user from a project"""
        try:
            member = self.db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            ).first()
            
            if not member:
                raise ValueError("User is not a member of this project")
            
            self.db.delete(member)
            self.db.commit()
            
            logger.info(f"User {user_id} removed from project {project_id}")
            return True
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing project member: {str(e)}")
            raise
    
    def get_project_members(self, project_id: str):
        """Get all members of a project"""
        try:
            members = self.db.query(User).join(
                ProjectMember
            ).filter(
                ProjectMember.project_id == project_id
            ).all()
            return members
        except Exception as e:
            logger.error(f"Error getting project members: {str(e)}")
            return []
    
    # ============================================
    # Task Operations
    # ============================================
    
    def create_task(self, task_data: TaskCreate) -> Task:
        """
        Create a new task for a project
        
        Args:
            task_data: TaskCreate schema
            
        Returns:
            Task object
            
        Raises:
            ValueError: If project not found
        """
        try:
            # Verify project exists
            project = self.get_project(task_data.project_id)
            if not project:
                raise ValueError("Project not found")
            
            task = Task(
                title=task_data.title,
                description=task_data.description,
                project_id=task_data.project_id,
                priority=task_data.priority or TaskPriority.MEDIUM,
                status=TaskStatus.PENDING,
                deadline=task_data.deadline,
                requirements=task_data.requirements or []
            )
            
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            
            logger.info(f"Task created successfully: {task.id} - {task.title}")
            
            return task
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating task: {str(e)}")
            raise
    
    def get_task(self, task_id: str) -> Task:
        """Get task by ID"""
        try:
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.warning(f"Task not found: {task_id}")
            return task
        except Exception as e:
            logger.error(f"Error getting task: {str(e)}")
            return None
    
    def get_project_tasks(self, project_id: str):
        """Get all tasks for a project"""
        try:
            tasks = self.db.query(Task).filter(
                Task.project_id == project_id
            ).all()
            return tasks
        except Exception as e:
            logger.error(f"Error getting project tasks: {str(e)}")
            return []
    
    def update_task(self, task_id: str, **kwargs) -> Task:
        """Update task information"""
        try:
            task = self.get_task(task_id)
            if not task:
                raise ValueError("Task not found")
            
            for key, value in kwargs.items():
                if hasattr(task, key) and value is not None:
                    setattr(task, key, value)
            
            task.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(task)
            
            logger.info(f"Task updated: {task_id}")
            return task
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating task: {str(e)}")
            raise
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> Task:
        """Update task status"""
        return self.update_task(task_id, status=status)
    
    # ============================================
    # Assignment Operations
    # ============================================
    
    def create_assignment(
        self,
        user_id: str,
        task_id: str,
        project_id: str
    ) -> Assignment:
        """
        Create a new assignment
        
        Args:
            user_id: User being assigned
            task_id: Task to assign
            project_id: Project ID
            
        Returns:
            Assignment object
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Check if assignment already exists
            existing = self.db.query(Assignment).filter(
                Assignment.user_id == user_id,
                Assignment.task_id == task_id
            ).first()
            
            if existing:
                raise ValueError("Assignment already exists for this user and task")
            
            # Verify user, task, and project exist
            user = self.get_user(user_id)
            task = self.get_task(task_id)
            project = self.get_project(project_id)
            
            if not user:
                raise ValueError("User not found")
            if not task:
                raise ValueError("Task not found")
            if not project:
                raise ValueError("Project not found")
            
            # Add user to project if not already a member
            self.add_project_member(project_id, user_id)
            
            assignment = Assignment(
                user_id=user_id,
                task_id=task_id,
                project_id=project_id,
                status=AssignmentStatus.PENDING
            )
            
            self.db.add(assignment)
            self.db.commit()
            self.db.refresh(assignment)
            
            logger.info(f"Assignment created: {assignment.id}")
            
            return assignment
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating assignment: {str(e)}")
            raise
    
    def get_assignment(self, assignment_id: str) -> Assignment:
        """Get assignment by ID"""
        try:
            assignment = self.db.query(Assignment).filter(
                Assignment.id == assignment_id
            ).first()
            if not assignment:
                logger.warning(f"Assignment not found: {assignment_id}")
            return assignment
        except Exception as e:
            logger.error(f"Error getting assignment: {str(e)}")
            return None
    
    def get_user_assignments(self, user_id: str):
        """Get all assignments for a user"""
        try:
            assignments = self.db.query(Assignment).filter(
                Assignment.user_id == user_id
            ).all()
            return assignments
        except Exception as e:
            logger.error(f"Error getting user assignments: {str(e)}")
            return []
    
    def get_task_assignments(self, task_id: str):
        """Get all assignments for a task"""
        try:
            assignments = self.db.query(Assignment).filter(
                Assignment.task_id == task_id
            ).all()
            return assignments
        except Exception as e:
            logger.error(f"Error getting task assignments: {str(e)}")
            return []
    
    def update_assignment_status(
        self,
        assignment_id: str,
        status: AssignmentStatus
    ) -> Assignment:
        """Update assignment status"""
        try:
            assignment = self.get_assignment(assignment_id)
            if not assignment:
                raise ValueError("Assignment not found")
            
            assignment.status = status
            assignment.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(assignment)
            
            logger.info(f"Assignment status updated: {assignment_id} -> {status}")
            return assignment
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating assignment status: {str(e)}")
            raise
    
    def update_assignment_zalo_info(
        self,
        assignment_id: str,
        zalo_link: str,
        zalo_oa_id: str = None
    ) -> Assignment:
        """Update Zalo information for assignment"""
        try:
            assignment = self.get_assignment(assignment_id)
            if not assignment:
                raise ValueError("Assignment not found")
            
            assignment.zalo_link = zalo_link
            if zalo_oa_id:
                assignment.zalo_oa_id = zalo_oa_id
            
            self.db.commit()
            self.db.refresh(assignment)
            
            logger.info(f"Assignment Zalo info updated: {assignment_id}")
            return assignment
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating assignment Zalo info: {str(e)}")
            raise
    
    def update_assignment_agent_notes(
        self,
        assignment_id: str,
        agent_notes: dict
    ) -> Assignment:
        """Update agent analysis notes"""
        try:
            assignment = self.get_assignment(assignment_id)
            if not assignment:
                raise ValueError("Assignment not found")
            
            assignment.agent_notes = agent_notes
            self.db.commit()
            self.db.refresh(assignment)
            
            logger.info(f"Assignment agent notes updated: {assignment_id}")
            return assignment
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating agent notes: {str(e)}")
            raise
    
    def get_project_assignments(self, project_id: str):
        """Get all assignments for a project"""
        try:
            assignments = self.db.query(Assignment).filter(
                Assignment.project_id == project_id
            ).all()
            return assignments
        except Exception as e:
            logger.error(f"Error getting project assignments: {str(e)}")
            return []
    
    def get_pending_assignments(self):
        """Get all pending assignments"""
        try:
            assignments = self.db.query(Assignment).filter(
                Assignment.status == AssignmentStatus.PENDING
            ).all()
            return assignments
        except Exception as e:
            logger.error(f"Error getting pending assignments: {str(e)}")
            return []
    
    # ============================================
    # Statistics & Reporting
    # ============================================
    
    def get_project_stats(self, project_id: str) -> dict:
        """Get statistics for a project"""
        try:
            project = self.get_project(project_id)
            if not project:
                raise ValueError("Project not found")
            
            tasks = self.db.query(Task).filter(Task.project_id == project_id).all()
            assignments = self.get_project_assignments(project_id)
            members = self.get_project_members(project_id)
            
            completed_tasks = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
            pending_tasks = len([t for t in tasks if t.status == TaskStatus.PENDING])
            in_progress_tasks = len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])
            
            return {
                "project_id": project_id,
                "project_name": project.name,
                "total_tasks": len(tasks),
                "completed_tasks": completed_tasks,
                "pending_tasks": pending_tasks,
                "in_progress_tasks": in_progress_tasks,
                "total_assignments": len(assignments),
                "pending_assignments": len([a for a in assignments if a.status == AssignmentStatus.PENDING]),
                "total_members": len(members),
                "completion_percentage": round((completed_tasks / len(tasks) * 100) if tasks else 0, 2)
            }
        
        except Exception as e:
            logger.error(f"Error getting project stats: {str(e)}")
            return {}
    
    def get_user_stats(self, user_id: str) -> dict:
        """Get statistics for a user"""
        try:
            user = self.get_user(user_id)
            if not user:
                raise ValueError("User not found")
            
            assignments = self.get_user_assignments(user_id)
            completed = len([a for a in assignments if a.status == AssignmentStatus.COMPLETED])
            in_progress = len([a for a in assignments if a.status == AssignmentStatus.IN_PROGRESS])
            pending = len([a for a in assignments if a.status == AssignmentStatus.PENDING])
            
            return {
                "user_id": user_id,
                "user_name": user.name,
                "total_assignments": len(assignments),
                "completed": completed,
                "in_progress": in_progress,
                "pending": pending,
                "skills": user.skills,
                "role": user.role
            }
        
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return {}