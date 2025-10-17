from typing import Dict, Any, Optional
import httpx
import requests
import logging
import os
from dotenv import load_dotenv
import json
import urllib.parse

load_dotenv()

logger = logging.getLogger(__name__)

class ZaloService:
    """
    Low-level Zalo OA API client
    Responsible for direct API calls to Zalo platform
    """
    
    def __init__(self):
        self.zalo_base_url = os.getenv("ZALO_BASE_URL", "https://openapi.zalo.me")
        self.zalo_access_token = os.getenv("ZALO_ACCESS_TOKEN", "")
        self.zalo_oa_id = os.getenv("ZALO_OA_ID", "")
    
    async def get_oa_info(self) -> Dict[str, Any]:
        """Get Zalo OA information"""
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
    
    async def send_message(
        self,
        user_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send text message to user via Zalo OA
        
        Args:
            user_id: Zalo user ID
            text: Message text content
            metadata: Optional metadata to attach
            
        Returns:
            bool: True if message sent successfully
        """
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "access_token": self.zalo_access_token,
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "recipient": {
                        "user_id": user_id
                    },
                    "message": {
                        "text": text
                    }
                }
                
                if metadata:
                    payload["metadata"] = metadata
                
                response = await client.post(
                    f"{self.zalo_base_url}/v3.0/oa/message/cs",
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"Message sent to user: {user_id}")
                    return True
                else:
                    logger.error(f"Zalo API error: {response.status_code} - {response.text}")
                    return False
        
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return False
    
    async def get_conversation(
        self,
        user_id: str | int,
        count: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Retrieve conversation history with a Zalo user
        
        Args:
            user_id: Zalo user ID
            count: Number of messages to retrieve
            offset: Offset for pagination
            
        Returns:
            Dict containing conversation data
        """
        try:
            # Ensure numeric user_id when possible
            try:
                user_id_val = int(user_id)
            except Exception:
                user_id_val = user_id

            payload = {"offset": offset, "user_id": user_id_val, "count": count}
            data_str = json.dumps(payload, separators=(",", ":"))
            data_quoted = urllib.parse.quote(data_str, safe="")

            url = f"{self.zalo_base_url}/v2.0/oa/conversation?data={data_quoted}"
            headers = {
                "access_token": self.zalo_access_token,
                "Content-Type": "application/json"
            }

            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                try:
                    return resp.json()
                except Exception:
                    logger.error("Failed to parse JSON from Zalo conversation response")
                    return {"data": [], "raw_text": resp.text}
            else:
                logger.error(f"Zalo conversation API error: {resp.status_code} - {resp.text}")
                return {"data": [], "error": f"status_code={resp.status_code}"}

        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}")
            return {"data": [], "error": str(e)}
    
    async def download_file(self, file_url: str) -> bytes:
        """
        Download file from Zalo
        
        Args:
            file_url: URL of the file to download
            
        Returns:
            bytes: File content
        """
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.zalo_access_token}"
                }
                
                response = await client.get(file_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                logger.info(f"File downloaded from: {file_url}")
                return response.content
        
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            raise