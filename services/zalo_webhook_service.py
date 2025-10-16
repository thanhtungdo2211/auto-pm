import os
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

import httpx
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ZaloWebhookService:
    """Service to handle Zalo webhook events and user registration"""
    
    def __init__(self, cv_analyzer=None):
        self.zalo_access_token = os.getenv("ZALO_ACCESS_TOKEN", "")
        self.zalo_oa_id = os.getenv("ZALO_OA_ID", "")
        self.zalo_base_url = os.getenv("ZALO_BASE_URL", "https://openapi.zalo.me")
        self.hr_user_id = os.getenv("HR_USER_ID", "")
        self.upload_dir = Path("uploads/cvs")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.cv_analyzer = cv_analyzer
        self._cv_cache = {}
        self._pending_registrations = {}
    
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

📄 Yêu cầu CV bao gồm:
- ✅ File định dạng PDF
- ✅ Họ tên đầy đủ
- ✅ Email liên hệ
- ✅ Số điện thoại
- ✅ Kỹ năng và kinh nghiệm

Hệ thống sẽ tự động xử lý và thông báo kết quả cho bạn."""
                }
            }
            
            return await self.send_zalo_message(message)
        
        except Exception as e:
            logger.error(f"❌ Error sending registration instructions: {str(e)}")
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
                print(".....")
                logger.info(f"CV downloaded: {cv_path}")
                return cv_path
        
        except Exception as e:
            logger.error(f"Error downloading CV: {str(e)}")
            raise
    
    async def extract_cv_information(self, cv_path: Path) -> Dict[str, Any]:
        """
        Extract information from CV PDF using injected CV analyzer
        """
        if not self.cv_analyzer:
            logger.error("CV analyzer not configured")
            return self._get_default_cv_data("CV analyzer not configured")
        
        try:
            # Check cache first
            cv_path_str = str(cv_path)
            if cv_path_str in self._cv_cache:
                logger.info(f"Using cached CV data for: {cv_path}")
                return self._cv_cache[cv_path_str]
            
            logger.info(f"Extracting CV information from: {cv_path}")
            
            # Use injected CV analyzer
            result = self.cv_analyzer.query(cv_path_str)
            
            if not result or not result.candidates:
                logger.error("No candidate data extracted from CV")
                return self._get_default_cv_data("CV extraction failed")
            
            # Get first candidate
            candidate = result.candidates[0]
            
            # Map to user schema format
            cv_data = {
                "name": candidate.name or "Unknown",
                "email": candidate.email,
                "phone": candidate.phone,
                "skills": candidate.skills or [],
                "description": self._build_description(candidate),
                "experience_years": candidate.experience_years,
                "experience_level": candidate.experience_level,
                "role": candidate.role,
                "projects": [
                    {
                        "name": p.name,
                        "role": p.role,
                        "contribution": p.contribution
                    } for p in (candidate.projects or [])
                ],
                "strengths": candidate.strengths or []
            }
            
            # Cache the result
            self._cv_cache[cv_path_str] = cv_data
            
            logger.info(f"Successfully extracted CV data for: {cv_data['name']}")
            return cv_data
            
        except Exception as e:
            logger.error(f"Error extracting CV information: {str(e)}")
            return self._get_default_cv_data(f"CV extraction error: {str(e)}")
    
    def _get_default_cv_data(self, error_msg: str) -> Dict[str, Any]:
        """Return default CV data structure"""
        return {
            "name": "Unknown",
            "email": None,
            "phone": None,
            "skills": [],
            "description": error_msg
        }
    
    def _build_description(self, candidate) -> str:
        """Build description from candidate data"""
        parts = []
        
        if candidate.role:
            parts.append(f"Role: {candidate.role}")
        
        if candidate.experience_years:
            parts.append(f"Experience: {candidate.experience_years} years")
        
        if candidate.experience_level:
            parts.append(f"Level: {candidate.experience_level}")
        
        if candidate.strengths:
            parts.append(f"Strengths: {', '.join(candidate.strengths)}")
        
        if candidate.projects:
            parts.append(f"Projects: {len(candidate.projects)} projects")
        
        return " | ".join(parts) if parts else "No description available"
    
    async def notify_hr(self, registration_id: str, user_data: Dict[str, Any]) -> bool:
        """Send notification to HR about new registration with approval buttons"""
        try:
            # Format skills list
            skills_text = ', '.join(user_data.get('skills', [])) if user_data.get('skills') else 'N/A'
            
            # Format phone number
            phone = user_data.get('phone', 'N/A')
            
            # Format projects
            projects_text = ""
            projects = user_data.get('projects', [])
            if projects:
                for i, project in enumerate(projects[:3], 1):  # Show max 3 projects
                    projects_text += f"\n  {i}. {project.get('name', 'N/A')} - {project.get('role', 'N/A')}"
            else:
                projects_text = "\n  Không có dự án"
            
            # Format strengths
            strengths = user_data.get('strengths', [])
            strengths_text = ', '.join(strengths) if strengths else 'N/A'
            
            message = {
                "recipient": {
                    "user_id": self.hr_user_id
                },
                "message": {
                    "text": f"""🆕 ĐƠN ĐĂNG KÝ MỚI CẦN DUYỆT

👤 Họ tên: {user_data.get('name', 'N/A')}
📧 Email: {user_data.get('email', 'N/A')}
📱 Số điện thoại: {phone}
💼 Vị trí: {user_data.get('role', 'N/A')}
⭐ Cấp độ: {user_data.get('experience_level', 'N/A')}
📅 Kinh nghiệm: {user_data.get('experience_years', 'N/A')} năm
💡 Điểm mạnh: {strengths_text}
💪 Kỹ năng: {skills_text}
📂 Dự án:{projects_text}

🆔 Registration ID: {registration_id}

Vui lòng xem xét và phản hồi:
✅ Gõ: APPROVE {registration_id} để chấp nhận
❌ Gõ: DECLINE {registration_id} để từ chối"""
                }
            }
            
            return await self.send_zalo_message(message)
        
        except Exception as e:
            logger.error(f"❌ Error notifying HR: {str(e)}")
            return False
    
    def store_pending_registration(self, cv_data: Dict[str, Any], cv_path: str, user_id_zalo: str) -> str:
        """Store pending registration and return registration ID"""
        registration_id = str(uuid.uuid4())
        self._pending_registrations[registration_id] = {
            "cv_data": cv_data,
            "cv_path": cv_path,
            "user_id_zalo": user_id_zalo,
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"Stored pending registration: {registration_id}")
        return registration_id
    
    def get_pending_registration(self, registration_id: str) -> Optional[Dict[str, Any]]:
        """Get pending registration by ID"""
        return self._pending_registrations.get(registration_id)
    
    def remove_pending_registration(self, registration_id: str):
        """Remove pending registration after processing"""
        if registration_id in self._pending_registrations:
            del self._pending_registrations[registration_id]
            logger.info(f"Removed pending registration: {registration_id}")
    
    async def handle_text_message(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle text messages from users"""
        try:
            message = event_data.get("message", {})
            text = message.get("text", "").strip()
            user_id = event_data.get("sender", {}).get("id")
            
            logger.info(f"Received text from {user_id}: {text}")
            
            # Check if it's HR responding
            if user_id == self.hr_user_id:
                # Check for APPROVE command
                if text.upper().startswith("APPROVE "):
                    registration_id = text.split(" ", 1)[1].strip()
                    return {
                        "status": "success",
                        "action": "hr_approved",
                        "registration_id": registration_id
                    }
                
                # Check for DECLINE command
                elif text.upper().startswith("DECLINE "):
                    registration_id = text.split(" ", 1)[1].strip()
                    return {
                        "status": "success",
                        "action": "hr_declined",
                        "registration_id": registration_id
                    }
            
            # Check if user wants to register
            if text.lower() in ["đăng ký", "dang ky", "register"]:
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
    
    async def send_approval_notification(self, user_id_zalo: str, user_data: Dict[str, Any]) -> bool:
        """Send approval notification to candidate"""
        try:
            phone_text = f"\n📱 SĐT: {user_data.get('phone')}" if user_data.get('phone') else ""
            
            message = {
                "recipient": {
                    "user_id": user_id_zalo
                },
                "message": {
                    "text": f"""✅ ĐƠN ĐĂNG KÝ ĐÃ ĐƯỢC DUYỆT!

Chúc mừng {user_data.get('name')}!
Đơn đăng ký của bạn đã được HR phê duyệt.

📋 Thông tin tài khoản:
👤 Tên: {user_data.get('name')}
📧 Email: {user_data.get('email')}{phone_text}
🆔 ID: {user_data.get('id')}

HR sẽ liên hệ với bạn trong thời gian sớm nhất.
Cảm ơn bạn đã đăng ký!"""
                }
            }
            
            return await self.send_zalo_message(message)
        
        except Exception as e:
            logger.error(f"❌ Error sending approval notification: {str(e)}")
            return False
    
    async def send_rejection_notification(self, user_id_zalo: str, name: str) -> bool:
        """Send rejection notification to candidate"""
        try:
            message = {
                "recipient": {
                    "user_id": user_id_zalo
                },
                "message": {
                    "text": f"""THÔNG BÁO TỪ HR

Xin chào {name},

Rất tiếc, đơn đăng ký của bạn chưa được chấp nhận lúc này.

Chúng tôi đã xem xét hồ sơ của bạn nhưng hiện tại vị trí chưa phù hợp.

Cảm ơn bạn đã quan tâm. Chúc bạn thành công!"""
                }
            }
            
            return await self.send_zalo_message(message)
        
        except Exception as e:
            logger.error(f"Error sending rejection notification: {str(e)}")
            return False
    
    async def send_pending_notification(self, user_id_zalo: str, name: str) -> bool:
        """Send pending notification to candidate after CV submission"""
        try:
            message = {
                "recipient": {
                    "user_id": user_id_zalo
                },
                "message": {
                    "text": f"""📄 CV ĐÃ ĐƯỢC GỬI THÀNH CÔNG!

Xin chào {name},

CV của bạn đã được hệ thống tiếp nhận và đang chờ HR xem xét.

⏳ Trạng thái: Đang chờ duyệt
📧 Chúng tôi sẽ thông báo kết quả cho bạn sớm nhất.

Cảm ơn bạn đã quan tâm!"""
                }
            }
            
            return await self.send_zalo_message(message)
        
        except Exception as e:
            logger.error(f"Error sending pending notification: {str(e)}")
            return False
    
    async def send_zalo_message(self, message_data: Dict[str, Any]) -> bool:
        """Send message via Zalo OA API"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "access_token": self.zalo_access_token,
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