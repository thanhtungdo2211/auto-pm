import os
import logging
import json
from typing import Dict, Any, Optional
import httpx
from dotenv import load_dotenv
from datetime import datetime

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
        self.chatbot_log_file = os.getenv("CHATBOT_LOG_FILE", "data/chatbot_requests.log")
        # Ensure log directory exists
        try:
            os.makedirs(os.path.dirname(self.chatbot_log_file), exist_ok=True)
        except Exception:
            # If dirname is empty (current dir), skip
            pass
        # Lưu mode_report theo user_id để sử dụng lại lần query tiếp theo
        self.user_mode_report = {}  # {user_id: mode_report}

    def _log_chat_request(self, payload: Dict[str, Any]):
        """
        Append outbound chatbot payload to a log file for debugging/testing.
        """
        try:
            record = {
                "ts": datetime.now().isoformat(),
                "payload": payload,
            }
            with open(self.chatbot_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.error("Failed to log chatbot payload: %s", exc)
    
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
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                payload = {
                    "user_id": int(user_id) if user_id.isdigit() else hash(user_id) % (10 ** 10),
                    "query": query,
                    "file": "",  # Empty file for text-only queries
                    "long_memory": ""
                }
                
                logger.info(f"Sending query to chatbot for user {user_id}: {query[:50]}...")
                
                response = await client.post(
                    f"{self.chatbot_url}",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    chatbot_response = data.get("response", "")
                    logger.info(f"Chatbot response received for user {user_id}")
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
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                # If query is None, use empty string
                query_text = query if query else ""
                
                payload = {
                    "user_id": int(user_id) if user_id.isdigit() else hash(user_id) % (10 ** 10),
                    "query": query_text,
                    "file_content": file_content,
                    "long_memory": ""
                }
                # print(payload)
                logger.info(f"Sending file to chatbot for user {user_id}")
                logger.info(f"File: {file_name}, Content length: {len(file_content)} chars, Query: '{query_text}'")
                logger.info(f"Payload preview: user_id={payload['user_id']}, query='{payload['query'][:50]}...', file_length={len(payload['file_content'])}")
                
                response = await client.post(
                    f"{self.chatbot_url}",
                    json=payload
                )
                

                if response.status_code == 200:
                    data = response.json()
                    chatbot_response = data.get("response", "")
                    logger.info(f"Chatbot processed file for user {user_id}")
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
    
    async def send_long_memory(
        self, 
        user_id: str, 
        query: str,
        long_memory: str
    ) -> Optional[str]:
        """
        Send only long memory to chatbot (no query, no file)
        Used for updating user context/history without triggering a response
        
        Args:
            user_id: User ID
            long_memory: Long-term memory content (conversation history, user context, etc.)
            
        Returns:
            str: Chatbot response or None if error
        """
        if not self.chatbot_url:
            logger.error("Chatbot URL not configured")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                payload = {
                    "user_id": int(user_id) if user_id.isdigit() else hash(user_id) % (10 ** 10),
                    "query": query,  # Empty query
                    "file": "",   # Empty file
                    "long_memory": long_memory
                }
                
                logger.info(f"Sending long memory to chatbot for user {user_id}")
                logger.info(f"Long memory length: {len(long_memory)} chars")
                logger.info(f"Long memory preview: {long_memory[:200]}...")
                
                response = await client.post(
                    f"{self.chatbot_url}",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    chatbot_response = data.get("response", "")
                    logger.info(f"Long memory updated for user {user_id}")
                    return chatbot_response
                else:
                    logger.error(f"Chatbot API error: {response.status_code} - {response.text}")
                    return None
        
        except httpx.TimeoutException:
            logger.error(f"Chatbot API timeout for user {user_id} with long memory")
            return "Xin lỗi, hệ thống đang bận. Vui lòng thử lại sau."
        except Exception as e:
            logger.error(f"Error calling chatbot API with long memory: {str(e)}")
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

    async def send_chat_request(
        self,
        user_id: str,
        role: Optional[str],
        query: str,
        mode_report: Optional[bool] = None,
        file_content: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Gửi yêu cầu đến chatbot với đầy đủ tham số (role, mode_report, file_content).
        Dùng cho các tác vụ hẹn giờ (nhắc báo cáo staff, tổng hợp báo cáo cho manager).
        
        Nếu mode_report không được truyền vào (None), sẽ lấy từ lần response trước đó.
        Nếu chưa có lưu, mặc định là False.
        """
        if not self.chatbot_url:
            logger.error("Chatbot URL not configured")
            return None

        # Nếu mode_report không được truyền vào, lấy từ lần response trước đó
        if mode_report is None:
            mode_report = self.user_mode_report.get(user_id, False)
            logger.info(
                "Using saved mode_report=%s for user %s (from previous response)",
                mode_report,
                user_id,
            )

        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                payload = {
                    "user_id": int(user_id) if str(user_id).isdigit() else hash(user_id) % (10 ** 10),
                    "role": role or "",
                    "query": query or "",
                    "file_content": file_content or "",
                    "mode_report": mode_report,
                }

                # Log outbound payload for testing/debug
                self._log_chat_request(payload)

                logger.info(
                    "Sending chat request (mode_report=%s) to chatbot for user %s, role=%s",
                    mode_report,
                    user_id,
                    role,
                )

                response = await client.post(self.chatbot_url, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    response_mode_report = data.get("mode_report", mode_report)
                    
                    # Lưu mode_report từ response để dùng cho lần query tiếp theo
                    self.user_mode_report[user_id] = response_mode_report
                    logger.info(
                        "Saved mode_report=%s for user %s (from current response)",
                        response_mode_report,
                        user_id,
                    )
                    
                    return {
                        "response": data.get("response"),
                        "mode_report": response_mode_report,
                        "raw": data,
                    }

                logger.error(
                    "Chatbot API error: %s - %s",
                    response.status_code,
                    response.text,
                )
                return None

        except httpx.TimeoutException:
            logger.error("Chatbot API timeout for user %s (mode_report=%s)", user_id, mode_report)
            return None
        except Exception as exc:
            logger.error("Error calling chatbot API: %s", exc, exc_info=True)
            return None