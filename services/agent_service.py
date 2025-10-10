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


# ============================================
# services/zalo_service.py
# ============================================

import requests
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class ZaloService:
    """Service to manage Zalo OA integration"""
    
    def __init__(self):
        # Zalo OA Configuration
        self.zalo_base_url = os.getenv("ZALO_BASE_URL", "https://openapi.zalo.me")
        self.zalo_access_token = os.getenv("ZALO_ACCESS_TOKEN", "")
        self.zalo_oa_id = os.getenv("ZALO_OA_ID", "")
        self.server_base_url = os.getenv("SERVER_BASE_URL", "http://localhost:8000")
    
    async def generate_zalo_oa_link(
        self,
        user_id: str,
        assignment_id: str,
        task_id: str
    ) -> str:
        """
        Generate Zalo OA link for staff to join conversation
        Format: https://zalo.me/oa/{oa_id}/?data={assignment_id}
        """
        try:
            # Create a reference token/code that links assignment to Zalo conversation
            reference_code = f"{assignment_id}:{task_id}:{user_id}"
            
            # Zalo OA link format
            # You can customize this based on your Zalo OA setup
            zalo_link = f"https://zalo.me/oa/{self.zalo_oa_id}/?params=assignment_id:{assignment_id}"
            
            logger.info(f"Generated Zalo OA link for assignment: {assignment_id}")
            
            return zalo_link
        
        except Exception as e:
            logger.error(f"Error generating Zalo OA link: {str(e)}")
            raise
    
    async def get_zalo_oa_info(self) -> Dict[str, Any]:
        """
        Get Zalo OA information
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.zalo_access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.zalo_base_url}/v3/oa/getinfo",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Retrieved Zalo OA info")
                return response.json()
            else:
                logger.error(f"Zalo API error: {response.status_code}")
                raise Exception(f"Zalo API error: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error getting Zalo OA info: {str(e)}")
            raise
    
    async def send_zalo_message(
        self,
        user_id: str,
        assignment_id: str,
        message: str
    ) -> bool:
        """
        Send message to user via Zalo OA
        Can be used to notify staff about task assignment
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.zalo_access_token}",
                "Content-Type": "application/json"
            }
            
            # Message payload - customize based on your Zalo API version
            payload = {
                "recipient": {
                    "user_id": user_id
                },
                "message": {
                    "text": message
                },
                "metadata": {
                    "assignment_id": assignment_id
                }
            }
            
            response = requests.post(
                f"{self.zalo_base_url}/v3/oa/message/cs/send",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Message sent via Zalo for assignment: {assignment_id}")
                return True
            else:
                logger.error(f"Zalo message error: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending Zalo message: {str(e)}")
            return False
    
    async def create_zalo_conversion_link(
        self,
        assignment_id: str,
        user_email: str,
        task_title: str
    ) -> str:
        """
        Create a direct conversation link with pre-filled information
        This link will open Zalo with the task assignment context
        """
        try:
            # Create a deep link that includes assignment context
            # Format can be customized based on your needs
            conversation_link = (
                f"{self.server_base_url}/zalo/callback?"
                f"assignment_id={assignment_id}&"
                f"email={user_email}&"
                f"task={task_title}&"
                f"oa_id={self.zalo_oa_id}"
            )
            
            logger.info(f"Created conversation link for assignment: {assignment_id}")
            
            return conversation_link
        
        except Exception as e:
            logger.error(f"Error creating Zalo conversation link: {str(e)}")
            raise