from typing import Dict, Any

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
    
    async def send_text_message(
        self,
        user_id: str,
        text: str
    ) -> bool:
        """
        Send simple text message to user
        """
        try:
            payload = {
                "recipient": {
                    "user_id": user_id
                },
                "message": {
                    "text": text
                }
            }
            
            return await self.send_zalo_message(user_id, "", text)
        
        except Exception as e:
            logger.error(f"Error sending text message: {str(e)}")
            return False