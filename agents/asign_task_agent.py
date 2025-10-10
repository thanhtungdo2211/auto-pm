# agents/assign_task_agent.py
# Agent 1: Assign Task Agent (Chạy trên port 8001)
# Chức năng: Phân tích task và gợi ý các ứng cử viên phù hợp nhất

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Assign Task Agent", version="1.0.0")


class TaskAssignmentRequest(BaseModel):
    task_id: str
    title: str
    description: Optional[str]
    priority: str
    requirements: List[str]
    project_id: str
    deadline: Optional[str] = None


class CandidateSuggestion(BaseModel):
    user_id: str
    name: str
    email: str
    match_score: float
    skills_match: List[str]
    skills_gap: List[str]
    availability: str
    recommendation: str


class AssignTaskResponse(BaseModel):
    success: bool
    task_id: str
    title: str
    suggested_candidates: List[CandidateSuggestion]
    best_candidate: Optional[CandidateSuggestion] = None
    analysis: Dict[str, Any]
    timestamp: datetime


class TaskAnalyzer:
    """Analyze tasks and suggest candidates"""
    
    def __init__(self):
        # In production, connect to main database or use API
        self.candidates_db = self._init_mock_candidates()
    
    def _init_mock_candidates(self) -> List[Dict[str, Any]]:
        """Mock database of candidates"""
        return [
            {
                "user_id": "user-1",
                "name": "Nguyễn Văn A",
                "email": "user1@example.com",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
                "experience_years": 5,
                "availability": "available",
                "current_tasks": 2,
                "max_tasks": 5
            },
            {
                "user_id": "user-2",
                "name": "Trần Thị B",
                "email": "user2@example.com",
                "skills": ["Figma", "UI/UX", "Adobe XD", "Prototyping"],
                "experience_years": 4,
                "availability": "available",
                "current_tasks": 1,
                "max_tasks": 5
            },
            {
                "user_id": "user-3",
                "name": "Lê Văn C",
                "email": "user3@example.com",
                "skills": ["React", "JavaScript", "CSS", "HTML"],
                "experience_years": 3,
                "availability": "busy",
                "current_tasks": 4,
                "max_tasks": 5
            }
        ]
    
    def analyze_task(self, task_request: TaskAssignmentRequest) -> Dict[str, Any]:
        """
        Analyze task requirements and find best candidates
        """
        logger.info(f"Analyzing task: {task_request.title}")
        
        # Extract requirements
        required_skills = set(skill.lower() for skill in task_request.requirements)
        priority_weight = self._get_priority_weight(task_request.priority)
        
        # Score each candidate
        scored_candidates = []
        for candidate in self.candidates_db:
            score_data = self._score_candidate(
                candidate,
                required_skills,
                priority_weight
            )
            scored_candidates.append(score_data)
        
        # Sort by match score
        scored_candidates.sort(
            key=lambda x: x["match_score"],
            reverse=True
        )
        
        # Create suggestions
        suggestions = [
            CandidateSuggestion(
                user_id=c["user_id"],
                name=c["name"],
                email=c["email"],
                match_score=c["match_score"],
                skills_match=c["skills_match"],
                skills_gap=c["skills_gap"],
                availability=c["availability"],
                recommendation=c["recommendation"]
            )
            for c in scored_candidates
        ]
        
        analysis = {
            "required_skills": list(required_skills),
            "priority": task_request.priority,
            "total_candidates_evaluated": len(self.candidates_db),
            "suitable_candidates": len([s for s in suggestions if s.match_score >= 0.6]),
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Found {len(suggestions)} candidates")
        
        return {
            "suggestions": suggestions,
            "analysis": analysis
        }
    
    def _score_candidate(
        self,
        candidate: Dict[str, Any],
        required_skills: set,
        priority_weight: float
    ) -> Dict[str, Any]:
        """Calculate match score for a candidate"""
        
        candidate_skills = set(s.lower() for s in candidate["skills"])
        
        # Calculate skill match percentage
        skills_match = list(candidate_skills & required_skills)
        skills_gap = list(required_skills - candidate_skills)
        skill_match_percentage = (
            len(skills_match) / len(required_skills) if required_skills else 0
        )
        
        # Availability score
        availability_score = (
            1.0 if candidate["availability"] == "available" else 0.5
        )
        
        # Workload score
        workload_score = 1.0 - (
            candidate["current_tasks"] / candidate["max_tasks"]
        )
        
        # Experience score
        experience_score = min(candidate["experience_years"] / 10, 1.0)
        
        # Calculate overall match score (weighted)
        match_score = (
            skill_match_percentage * 0.5 +
            availability_score * 0.2 +
            workload_score * 0.2 +
            experience_score * 0.1
        ) * priority_weight
        
        # Generate recommendation
        if match_score >= 0.9:
            recommendation = "Perfect match! Highly recommended."
        elif match_score >= 0.7:
            recommendation = "Good match. Suitable for this task."
        elif match_score >= 0.5:
            recommendation = "Acceptable match. May need support."
        else:
            recommendation = "Below average. Consider alternative candidates."
        
        return {
            "user_id": candidate["user_id"],
            "name": candidate["name"],
            "email": candidate["email"],
            "match_score": round(match_score, 2),
            "skills_match": skills_match,
            "skills_gap": skills_gap,
            "availability": candidate["availability"],
            "recommendation": recommendation,
            "details": {
                "skill_match_percentage": round(skill_match_percentage, 2),
                "availability_score": round(availability_score, 2),
                "workload_score": round(workload_score, 2),
                "experience_score": round(experience_score, 2)
            }
        }
    
    def _get_priority_weight(self, priority: str) -> float:
        """Get weight multiplier based on priority"""
        weights = {
            "low": 1.0,
            "medium": 1.1,
            "high": 1.3,
            "urgent": 1.5
        }
        return weights.get(priority.lower(), 1.0)


# Initialize analyzer
analyzer = TaskAnalyzer()


@app.post("/api/agents/assign-task", response_model=AssignTaskResponse)
async def assign_task_agent(request: TaskAssignmentRequest):
    """
    Main endpoint for Assign Task Agent
    Analyzes task and suggests best candidates
    """
    try:
        analysis_result = analyzer.analyze_task(request)
        
        suggestions = analysis_result["suggestions"]
        best_candidate = suggestions[0] if suggestions else None
        
        return AssignTaskResponse(
            success=True,
            task_id=request.task_id,
            title=request.title,
            suggested_candidates=suggestions,
            best_candidate=best_candidate,
            analysis=analysis_result["analysis"],
            timestamp=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Error in assign task agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "agent": "assign-task-agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


# ============================================
# agents/exchange_task_agent.py
# Agent 2: Task Exchange Agent (Chạy trên port 8002)
# Chức năng: Phân tích sự phù hợp giữa user và task, gợi ý tối ưu hóa

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Task Exchange Agent", version="1.0.0")


class UserInfo(BaseModel):
    id: str
    name: str
    email: str
    cv: Optional[str]
    description: Optional[str]
    skills: List[str]


class TaskInfo(BaseModel):
    id: str
    title: str
    description: Optional[str]
    priority: str
    deadline: Optional[str]


class ProjectInfo(BaseModel):
    id: str
    name: str
    description: Optional[str]


class ExchangeTaskRequest(BaseModel):
    assignment_id: str
    user: UserInfo
    task: TaskInfo
    project: ProjectInfo


class ExchangeTaskResponse(BaseModel):
    success: bool
    assignment_id: str
    match_score: float
    skills_match: List[str]
    skills_gap: List[str]
    can_optimize_swap: bool
    recommendations: List[str]
    analysis: Dict[str, Any]
    timestamp: datetime


class TaskExchanger:
    """Analyze and optimize task assignments"""
    
    def analyze_compatibility(self, request: ExchangeTaskRequest) -> Dict[str, Any]:
        """
        Analyze compatibility between user and task
        Suggest optimizations or task swaps
        """
        logger.info(f"Analyzing assignment: {request.assignment_id}")
        
        # Parse task requirements from description
        task_requirements = self._extract_requirements(request.task.description)
        user_skills = set(s.lower() for s in request.user.skills)
        
        # Calculate match
        skills_match = list(user_skills & set(s.lower() for s in task_requirements))
        skills_gap = list(set(s.lower() for s in task_requirements) - user_skills)
        
        match_percentage = (
            len(skills_match) / len(task_requirements)
            if task_requirements else 1.0
        )
        
        # Priority-adjusted score
        priority_weight = self._get_priority_multiplier(request.task.priority)
        match_score = round(match_percentage * priority_weight, 2)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            match_score,
            skills_gap,
            request.user,
            request.task
        )
        
        # Check if swap is beneficial
        can_optimize_swap = match_score < 0.6 and len(skills_gap) > 2
        
        analysis = {
            "user_id": request.user.id,
            "task_id": request.task.id,
            "project_id": request.project.id,
            "match_percentage": round(match_percentage, 2),
            "skills_count": len(request.user.skills),
            "required_skills": len(task_requirements),
            "gaps": len(skills_gap),
            "priority": request.task.priority,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return {
            "match_score": match_score,
            "skills_match": skills_match,
            "skills_gap": skills_gap,
            "can_optimize_swap": can_optimize_swap,
            "recommendations": recommendations,
            "analysis": analysis
        }
    
    def _extract_requirements(self, description: Optional[str]) -> List[str]:
        """Extract skills from task description"""
        if not description:
            return []
        
        # Common skill keywords
        keywords = [
            "python", "javascript", "react", "vue", "angular",
            "fastapi", "django", "flask", "nodejs",
            "sql", "postgresql", "mongodb", "redis",
            "docker", "kubernetes", "aws", "gcp",
            "ui/ux", "figma", "design", "prototyping",
            "agile", "scrum", "git", "ci/cd"
        ]
        
        found_skills = []
        desc_lower = description.lower()
        for keyword in keywords:
            if keyword in desc_lower:
                found_skills.append(keyword)
        
        return found_skills
    
    def _get_priority_multiplier(self, priority: str) -> float:
        """Get multiplier based on task priority"""
        multipliers = {
            "low": 1.0,
            "medium": 1.1,
            "high": 1.2,
            "urgent": 1.5
        }
        return multipliers.get(priority.lower(), 1.0)
    
    def _generate_recommendations(
        self,
        match_score: float,
        skills_gap: List[str],
        user: UserInfo,
        task: TaskInfo
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if match_score >= 0.9:
            recommendations.append("✓ User is highly suitable for this task")
            recommendations.append("✓ Proceed with assignment immediately")
        
        elif match_score >= 0.7:
            recommendations.append("✓ User is suitable for this task")
            if skills_gap:
                recommendations.append(
                    f"- Consider pairing with specialist in: {', '.join(skills_gap[:2])}"
                )
        
        elif match_score >= 0.5:
            recommendations.append("⚠ User has acceptable match")
            if skills_gap:
                recommendations.append(
                    f"- User lacks: {', '.join(skills_gap[:3])}"
                )
            recommendations.append("- Recommend training or mentorship")
        
        else:
            recommendations.append("✗ User has poor match for this task")
            recommendations.append("✗ Consider task reassignment")
            if skills_gap:
                recommendations.append(
                    f"- Critical gaps: {', '.join(skills_gap[:4])}"
                )
        
        # Add timeline recommendations
        if task.deadline:
            recommendations.append(
                "- Ensure user has sufficient time for task completion"
            )
        
        if match_score < 0.8 and skills_gap:
            recommendations.append(
                f"- Recommend learning resources for: {skills_gap[0]}"
            )
        
        return recommendations
    
    def suggest_task_optimization(
        self,
        request: ExchangeTaskRequest
    ) -> Optional[Dict[str, Any]]:
        """Suggest alternative assignments or task splits"""
        # This would connect to main database to find better matches
        return None


# Initialize exchanger
exchanger = TaskExchanger()


@app.post("/api/agents/exchange-task", response_model=ExchangeTaskResponse)
async def exchange_task_agent(request: ExchangeTaskRequest):
    """
    Main endpoint for Task Exchange Agent
    Analyzes assignment compatibility and suggests optimizations
    """
    try:
        analysis_result = exchanger.analyze_compatibility(request)
        
        return ExchangeTaskResponse(
            success=True,
            assignment_id=request.assignment_id,
            match_score=analysis_result["match_score"],
            skills_match=analysis_result["skills_match"],
            skills_gap=analysis_result["skills_gap"],
            can_optimize_swap=analysis_result["can_optimize_swap"],
            recommendations=analysis_result["recommendations"],
            analysis=analysis_result["analysis"],
            timestamp=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Error in exchange task agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "agent": "exchange-task-agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)