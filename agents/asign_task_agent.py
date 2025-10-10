# agents/exchange_task_agent.py
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
        """Analyze compatibility between user and task"""
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
        
        if task.deadline:
            recommendations.append(
                "- Ensure user has sufficient time for task completion"
            )
        
        if match_score < 0.8 and skills_gap:
            recommendations.append(
                f"- Recommend learning resources for: {skills_gap[0]}"
            )
        
        return recommendations

# Initialize exchanger
exchanger = TaskExchanger()

@app.post("/api/agents/exchange-task", response_model=ExchangeTaskResponse)
async def exchange_task_agent(request: ExchangeTaskRequest):
    """Main endpoint for Task Exchange Agent"""
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