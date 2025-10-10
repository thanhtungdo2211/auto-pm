import httpx
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from schemas import AgentResponse
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class AgentService:
    """Service to communicate with AI Agents"""
    
    def __init__(self):
        # Configure agent endpoints from environment
        self.assign_task_agent_url = os.getenv(
            "ASSIGN_TASK_AGENT_URL",
            "http://localhost:8001/api/agents/assign-task"
        )
        self.exchange_task_agent_url = os.getenv(
            "EXCHANGE_TASK_AGENT_URL",
            "http://localhost:8002/api/agents/exchange-task"
        )
        self.timeout = 30
    
    async def send_to_assign_agent(self, task) -> Optional[AgentResponse]:
        """
        Send task information to Assign Task Agent
        Agent will analyze task requirements and suggest suitable candidates
        """
        try:
            payload = {
                "task_id": task.id,
                "title": task.title,
                "description": task.description,
                "priority": task.priority.value if task.priority else "medium",
                "requirements": task.requirements or [],
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "project_id": task.project_id
            }
            
            async with httpx.AsyncClient() as client:
                response = await asyncio.wait_for(
                    client.post(
                        self.assign_task_agent_url,
                        json=payload,
                        timeout=self.timeout
                    ),
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Task sent to assign agent: {task.id}")
                    return AgentResponse(
                        success=True,
                        message="Task sent to assignment agent for analysis",
                        data=data,
                        agent_id="assign-task-agent"
                    )
                else:
                    logger.error(f"Assign agent error: {response.status_code}")
                    return AgentResponse(
                        success=False,
                        message=f"Assign agent returned status {response.status_code}",
                        agent_id="assign-task-agent"
                    )
        
        except asyncio.TimeoutError:
            logger.error("Timeout connecting to assign agent")
            return AgentResponse(
                success=False,
                message="Timeout connecting to assign agent",
                agent_id="assign-task-agent"
            )
        except Exception as e:
            logger.error(f"Error sending to assign agent: {str(e)}")
            return AgentResponse(
                success=False,
                message=f"Error: {str(e)}",
                agent_id="assign-task-agent"
            )
    
    async def send_to_exchange_agent(self, assignment_payload: Dict[str, Any]) -> Optional[AgentResponse]:
        """
        Send assignment info to Task Exchange Agent
        Agent will analyze user skills vs task requirements and suggest optimizations
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await asyncio.wait_for(
                    client.post(
                        self.exchange_task_agent_url,
                        json=assignment_payload,
                        timeout=self.timeout
                    ),
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Assignment sent to exchange agent: {assignment_payload['assignment_id']}")
                    return AgentResponse(
                        success=True,
                        message="Assignment analyzed by exchange agent",
                        data=data,
                        recommendations=data.get("recommendations", []),
                        agent_id="exchange-task-agent"
                    )
                else:
                    logger.error(f"Exchange agent error: {response.status_code}")
                    return AgentResponse(
                        success=False,
                        message=f"Exchange agent returned status {response.status_code}",
                        agent_id="exchange-task-agent"
                    )
        
        except asyncio.TimeoutError:
            logger.error("Timeout connecting to exchange agent")
            return AgentResponse(
                success=False,
                message="Timeout connecting to exchange agent",
                agent_id="exchange-task-agent"
            )
        except Exception as e:
            logger.error(f"Error sending to exchange agent: {str(e)}")
            return AgentResponse(
                success=False,
                message=f"Error: {str(e)}",
                agent_id="exchange-task-agent"
            )
