import os
import logging
from typing import Dict, Any, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class ChatbotAgentService:
    """
    Service for interacting with the chatbot manager API
    Handles conversation with users through the chatbot
    """
    
    def __init__(self):
        self.chatbot_url = os.getenv("CHATBOT_MANAGER_URL", "")
        if not self.chatbot_url:
            logger.warning("CHATBOT_MANAGER_URL not configured")
    
    async def send_query(self, user_id: str, query: str) -> Optional[str]:
        """
        Send user query to chatbot and get response
        
        Args:
            user_id: User ID (Zalo user ID)
            query: User's message/query
            
        Returns:
            str: Chatbot response or None if error
        """
        if not self.chatbot_url:
            logger.error("Chatbot URL not configured")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "user_id": int(user_id) if user_id.isdigit() else hash(user_id) % (10 ** 10),
                    "query": query,
                    "file": ""  # Empty file for text-only queries
                }
                
                logger.info(f"Sending query to chatbot for user {user_id}: {query[:50]}...")
                
                response = await client.post(
                    f"{self.chatbot_url}/chat",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    chatbot_response = data.get("response", "")
                    logger.info(f"✅ Chatbot response received for user {user_id}")
                    return chatbot_response
                else:
                    logger.error(f"Chatbot API error: {response.status_code} - {response.text}")
                    return None
        
        except httpx.TimeoutException:
            logger.error(f"Chatbot API timeout for user {user_id}")
            return "Xin lỗi, hệ thống đang bận. Vui lòng thử lại sau."
        except Exception as e:
            logger.error(f"Error calling chatbot API: {str(e)}")
            return None
    
    async def send_query_with_file(
        self, 
        user_id: str, 
        query: Optional[str],
        file_content: str,
        file_name: str = ""
    ) -> Optional[str]:
        """
        Send user query with file content to chatbot
        
        Args:
            user_id: User ID
            query: User's query/instruction (None for file-only processing)
            file_content: File content as string
            file_name: Original file name
            
        Returns:
            str: Chatbot response or None if error
        """
        if not self.chatbot_url:
            logger.error("Chatbot URL not configured")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:  # 2 min timeout for file processing
                payload = {
                    "user_id": int(user_id) if user_id.isdigit() else hash(user_id) % (10 ** 10),
                    "query": query if query else "",  # Empty string if None
                    "file": file_content
                }
                
                logger.info(f"Sending file to chatbot for user {user_id}")
                logger.info(f"File: {file_name}, Content length: {len(file_content)} chars, Query: {query or 'None'}")
                
                response = await client.post(
                    f"{self.chatbot_url}/chat",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    chatbot_response = data.get("response", "")
                    logger.info(f"✅ Chatbot processed file for user {user_id}")
                    return chatbot_response
                else:
                    logger.error(f"Chatbot API error: {response.status_code} - {response.text}")
                    return None
        
        except httpx.TimeoutException:
            logger.error(f"Chatbot API timeout for user {user_id} with file")
            return "Xin lỗi, file quá lớn hoặc hệ thống đang bận. Vui lòng thử lại sau."
        except Exception as e:
            logger.error(f"Error calling chatbot API with file: {str(e)}")
            return None
    
    async def get_conversation_response(
        self, 
        user_id: str, 
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get chatbot response with additional context
        
        Args:
            user_id: User ID
            message: User message
            context: Optional context information
            
        Returns:
            Dict with response and metadata
        """
        response_text = await self.send_query(user_id, message)
        
        return {
            "user_id": user_id,
            "query": message,
            "response": response_text,
            "success": response_text is not None,
            "context": context
        }