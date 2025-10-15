import httpx
import logging
from typing import Dict, Any, Optional
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class ZaloWebhookService:
    """Service to handle Zalo webhook events and user registration"""
    
    def __init__(self):
        self.zalo_access_token = os.getenv("ZALO_ACCESS_TOKEN", "")
        self.zalo_oa_id = os.getenv("ZALO_OA_ID", "")
        self.zalo_base_url = os.getenv("ZALO_BASE_URL", "https://openapi.zalo.me")
        self.hr_user_id = os.getenv("HR_USER_ID", "")
        self.upload_dir = Path("uploads/cvs")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def handle_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main webhook event handler
        Routes events to appropriate handlers based on event type
        """
        try:
            event_name = event_data.get("event_name", "")
            
            if event_name == "user_send_text":
                return await self.handle_text_message(event_data)
            elif event_name == "user_send_file":
                return await self.handle_file_message(event_data)
            elif event_name == "follow":
                return await self.handle_follow_event(event_data)
            else:
                logger.info(f"Unhandled event type: {event_name}")
                return {"status": "ignored", "event": event_name}
        
        except Exception as e:
            logger.error(f"Error handling webhook event: {str(e)}")
            raise
    
    async def handle_text_message(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle text messages from users"""
        try:
            message = event_data.get("message", {})
            text = message.get("text", "").strip().lower()
            user_id = event_data.get("sender", {}).get("id")
            
            logger.info(f"Received text from {user_id}: {text}")
            
            # Check if user wants to register
            if text in ["đăng ký", "dang ky", "register"]:
                await self.send_registration_instructions(user_id)
                return {
                    "status": "success",
                    "action": "registration_initiated",
                    "user_id": user_id
                }
            
            return {"status": "success", "action": "message_received"}
        
        except Exception as e:
            logger.error(f"Error handling text message: {str(e)}")
            raise
    
    async def handle_file_message(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file uploads (CV PDFs)"""
        try:
            message = event_data.get("message", {})
            attachments = message.get("attachments", [])
            user_id = event_data.get("sender", {}).get("id")
            
            for attachment in attachments:
                if attachment.get("type") == "file":
                    file_url = attachment.get("payload", {}).get("url")
                    file_name = attachment.get("payload", {}).get("name", "cv.pdf")
                    
                    if file_url and file_name.lower().endswith('.pdf'):
                        # Download CV
                        cv_path = await self.download_cv(file_url, user_id, file_name)
                        
                        # Extract information from CV
                        cv_data = await self.extract_cv_information(cv_path)
                        
                        # Return data for user creation
                        return {
                            "status": "success",
                            "action": "cv_received",
                            "user_id": user_id,
                            "cv_path": str(cv_path),
                            "cv_data": cv_data
                        }
            
            return {"status": "error", "message": "No valid PDF file found"}
        
        except Exception as e:
            logger.error(f"Error handling file message: {str(e)}")
            raise
    
    async def handle_follow_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle when user follows the OA"""
        try:
            user_id = event_data.get("follower", {}).get("id")
            
            # Send welcome message
            await self.send_welcome_message(user_id)
            
            return {
                "status": "success",
                "action": "user_followed",
                "user_id": user_id
            }
        
        except Exception as e:
            logger.error(f"Error handling follow event: {str(e)}")
            raise
    
    async def send_registration_instructions(self, user_id: str) -> bool:
        """Send registration instructions to user"""
        try:
            message = {
                "recipient": {
                    "user_id": user_id
                },
                "message": {
                    "text": """Chào bạn! 👋

Để đăng ký làm nhân viên, vui lòng gửi CV của bạn dưới dạng file PDF.

📄 Yêu cầu:
- File định dạng PDF
- Bao gồm thông tin: Họ tên, Email, Số điện thoại, Kỹ năng

Hệ thống sẽ tự động xử lý và thông báo kết quả cho bạn."""
                }
            }
            
            return await self.send_zalo_message(message)
        
        except Exception as e:
            logger.error(f"Error sending registration instructions: {str(e)}")
            return False
    
    async def send_welcome_message(self, user_id: str) -> bool:
        """Send welcome message to new follower"""
        try:
            message = {
                "recipient": {
                    "user_id": user_id
                },
                "message": {
                    "text": """Chào mừng bạn đến với Auto Project Manager! 🎉

Để đăng ký làm nhân viên, hãy gửi tin nhắn: "Đăng ký"

Chúng tôi sẽ hướng dẫn bạn các bước tiếp theo."""
                }
            }
            
            return await self.send_zalo_message(message)
        
        except Exception as e:
            logger.error(f"Error sending welcome message: {str(e)}")
            return False
    
    async def download_cv(self, file_url: str, user_id: str, file_name: str) -> Path:
        """Download CV file from Zalo"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.zalo_access_token}"
                }
                
                response = await client.get(file_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                # Save file
                cv_filename = f"{user_id}_{file_name}"
                cv_path = self.upload_dir / cv_filename
                
                with open(cv_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"CV downloaded: {cv_path}")
                return cv_path
        
        except Exception as e:
            logger.error(f"Error downloading CV: {str(e)}")
            raise
    
    async def extract_cv_information(self, cv_path: Path) -> Dict[str, Any]:
        """
        Extract information from CV PDF
        This is a placeholder - implement with your CV extraction tool
        """
        # TODO: Integrate with your CV extraction tool
        # For now, return placeholder data
        return {
            "name": "To be extracted",
            "email": "to_be_extracted@example.com",
            "phone": "0000000000",
            "skills": ["Python", "FastAPI"],
            "description": "Extracted from CV"
        }
    
    async def notify_hr(self, user_data: Dict[str, Any]) -> bool:
        """Send notification to HR about new registration"""
        try:
            message = {
                "recipient": {
                    "user_id": self.hr_user_id
                },
                "message": {
                    "text": f"""🆕 Đăng ký nhân viên mới!

👤 Tên: {user_data.get('name')}
📧 Email: {user_data.get('email')}
📱 SĐT: {user_data.get('phone')}
💼 Kỹ năng: {', '.join(user_data.get('skills', []))}

User ID: {user_data.get('id')}"""
                }
            }
            
            return await self.send_zalo_message(message)
        
        except Exception as e:
            logger.error(f"Error notifying HR: {str(e)}")
            return False
    
    async def send_zalo_message(self, message_data: Dict[str, Any]) -> bool:
        """Send message via Zalo OA API"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.zalo_access_token}",
                    "Content-Type": "application/json"
                }
                
                response = await client.post(
                    f"{self.zalo_base_url}/v3.0/oa/message/cs",
                    headers=headers,
                    json=message_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info("Zalo message sent successfully")
                    return True
                else:
                    logger.error(f"Zalo API error: {response.status_code} - {response.text}")
                    return False
        
        except Exception as e:
            logger.error(f"Error sending Zalo message: {str(e)}")
            return False
    
    async def send_success_notification(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Send success notification to newly registered user"""
        try:
            message = {
                "recipient": {
                    "user_id": user_id
                },
                "message": {
                    "text": f"""✅ Đăng ký thành công!

Thông tin của bạn đã được lưu vào hệ thống:
👤 Tên: {user_data.get('name')}
📧 Email: {user_data.get('email')}
🆔 ID: {user_data.get('id')}

HR sẽ liên hệ với bạn sớm nhất. Cảm ơn bạn đã đăng ký!"""
                }
            }
            
            return await self.send_zalo_message(message)
        
        except Exception as e:
            logger.error(f"Error sending success notification: {str(e)}")
            return False