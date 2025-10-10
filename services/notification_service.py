import asyncio
from enum import Enum
from typing import Dict, Any, Optional
import logging

from services.zalo_service import ZaloService

logger = logging.getLogger(__name__)

class NotificationType(str, Enum):
    TASK_ASSIGNED = "task_assigned"
    TASK_ACCEPTED = "task_accepted"
    TASK_COMPLETED = "task_completed"
    TASK_REJECTED = "task_rejected"
    MESSAGE = "message"

class NotificationService:
    """Service to handle notifications across multiple channels"""
    
    def __init__(self, zalo_service: ZaloService):
        self.zalo_service = zalo_service
    
    async def send_assignment_notification(
        self,
        user_email: str,
        user_id: str,
        assignment_id: str,
        task_title: str,
        project_name: str,
        zalo_link: str
    ):
        """
        Send notification when task is assigned
        """
        try:
            message = (
                f"Bạn vừa được giao nhiệm vụ mới!\n\n"
                f"Dự án: {project_name}\n"
                f"Nhiệm vụ: {task_title}\n"
                f"Vui lòng truy cập link Zalo để nhận chi tiết: {zalo_link}"
            )
            
            # Send via Zalo
            await self.zalo_service.send_zalo_message(
                user_id=user_id,
                assignment_id=assignment_id,
                message=message
            )
            
            logger.info(f"Assignment notification sent: {assignment_id}")
        
        except Exception as e:
            logger.error(f"Error sending assignment notification: {str(e)}")
