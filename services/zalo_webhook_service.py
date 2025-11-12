import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from app.Qdrant import QdrantDB
from services.sync_message_service import SyncMessageService
from services.utils import read_file_content

logger = logging.getLogger(__name__)

class ZaloWebhookService:
    """
    High-level webhook event handler
    Processes business logic for user registration and HR approval workflow
    """
    
    def __init__(self, zalo_service, cv_analyzer=None, chatbot_service=None, project_service=None):
        """
        Args:
            zalo_service: Instance of ZaloService for API calls
            cv_analyzer: CV analysis service
            chatbot_service: Chatbot agent service for general conversations
            project_service: Project service for user lookup
        """
        self.zalo_service = zalo_service
        self.cv_analyzer = cv_analyzer
        self.chatbot_service = chatbot_service
        self.project_service = project_service
        self.hr_user_id = os.getenv("HR_USER_ID", "")
        
        # Create separate upload directories
        self.upload_dir = Path("uploads")
        self.cv_dir = self.upload_dir / "cvs"
        self.wbs_dir = self.upload_dir / "wbs"
        self.cv_dir.mkdir(parents=True, exist_ok=True)
        self.wbs_dir.mkdir(parents=True, exist_ok=True)
        
        #Long memory 
        self.qdrantdb = QdrantDB(vector_size= 768)
        self.embed = SyncMessageService()

        # In-memory storage (use database in production)
        self._cv_cache = {}
        self._pending_registrations = {}
        self._recent_messages_with_attachments = {}
    
    def _get_user_role(self, zalo_user_id: str) -> str:
        """
        Determine user role based on Zalo ID
        
        Returns:
            str: 'hr', 'manager', 'staff', or 'unknown'
        """
        # Check if HR
        if zalo_user_id == self.hr_user_id:
            return 'hr'
        
        # Check in database
        if self.project_service:
            user = self.project_service.get_user_by_zalo_id(zalo_user_id)
            if user:
                return user.role or 'staff'
            
        return 'unknown'
    
    def _detect_file_type(self, file_name: str, user_role: str) -> str:
        """
        Detect file type based on filename pattern and user role
        
        Args:
            file_name: Name of the file
            user_role: Role of the user sending the file
            
        Returns:
            str: 'cv', 'wbs', 'unknown'
        """
        file_name_lower = file_name.lower()
        
        # CV patterns - only for HR or unknown users
        if user_role in ['hr', 'unknown']:
            cv_patterns = [
                r'cv[-_\.]',          # cv-, cv_, cv.
                r'[-_]cv[-_\.]',      # -cv-, _cv_, -cv., _cv.
                r'^cv\.',             # cv.pdf
                r'resume',
                r'curriculum',
                r'ho[-_]so'           # hồ sơ
            ]
            
            for pattern in cv_patterns:
                if re.search(pattern, file_name_lower):
                    return 'cv'
        
        # WBS patterns - only for managers
        if user_role == 'manager':
            wbs_patterns = [
                r'wbs[-_\.]',                           # wbs-, wbs_, wbs.
                r'[-_]wbs[-_\.]',                       # -wbs-, _wbs_
                r'^wbs\.',                              # wbs.xlsx
                r'work[-_]breakdown',
                r'phan[-_]chia[-_]cong[-_]viec',       # phân chia công việc
                r'ke[-_]hoach',                         # kế hoạch
                r'task[-_]breakdown',
                r'project[-_]plan'
            ]
            
            for pattern in wbs_patterns:
                if re.search(pattern, file_name_lower):
                    return 'wbs'
        
        return 'unknown'
    
    async def handle_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main webhook event router
        Delegates to specific handlers based on event type
        """
        try:
            event_name = event_data.get("event_name", "")
            
            handlers = {
                "user_send_text": self.handle_text_message,
                "user_send_file": self.handle_file_message,
                "user_send_image": self.handle_image_message,
                "follow": self.handle_follow_event
            }
            
            handler = handlers.get(event_name)
            if handler:
                return await handler(event_data)
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
            text = message.get("text", "").strip()
            user_id = event_data.get("sender", {}).get("id")
            
            logger.info(f"Received text from {user_id}: {text}")
            
            # HR approval/decline commands
            if user_id == self.hr_user_id:
                if text.upper().startswith("APPROVE "):
                    registration_id = text.split(" ", 1)[1].strip()
                    return {
                        "status": "success",
                        "action": "hr_approved",
                        "registration_id": registration_id
                    }
                
                elif text.upper().startswith("DECLINE "):
                    registration_id = text.split(" ", 1)[1].strip()
                    return {
                        "status": "success",
                        "action": "hr_declined",
                        "registration_id": registration_id
                    }
            
            # User registration commands
            if text.lower() in ["đăng ký", "dang ky", "register"]:
                await self.send_registration_instructions(user_id)
                return {
                    "status": "success",
                    "action": "registration_initiated",
                    "user_id": user_id
                }
            
            # Handle general conversation with chatbot
            if self.chatbot_service:
                logger.info(f"Sending message to chatbot for user {user_id}")

                ###
                result = self.qdrantdb.search_one(user_id, self.embed.embed_query(text))
                logging.info(result)
                logging.info(self.qdrantdb.list_points(user_id))
                chatbot_response = await self.chatbot_service.send_long_memory(user_id=user_id, 
                                                            query=text,
                                                            long_memory=str(result))
                ###

                # chatbot_response = await self.chatbot_service.send_query(user_id, text)
                
                if chatbot_response:
                    await self.zalo_service.send_message(user_id, chatbot_response)
                    self.qdrantdb.upsert_one(
                        user_id = user_id, 
                        vector = self.embed.embed_query(text),
                        payload = {
                            "role": "user",
                            "text": text
                        } 
                    )
                    self.qdrantdb.upsert_one(
                        user_id = user_id, 
                        vector = self.embed.embed_query(chatbot_response),
                        payload = {
                            "role": "chatbot",
                            "text": chatbot_response
                        } 
                    )
                    return {
                        "status": "success",
                        "action": "chatbot_response_sent",
                        "user_id": user_id,
                        "query": text,
                        "response": chatbot_response
                    }
                    
                else:
                    self.qdrantdb.upsert_one(
                        user_id = user_id, 
                        vector = self.embed.embed_query(text),
                        payload = {
                            "role": "user",
                            "text": text
                        } 
                    )
                    result = self.qdrantdb.search_one(user_id, self.embed.embed_query(text))
                    logging.info(result)
                    logging.info(self.qdrantdb.list_points(user_id))
                    fallback_message = "Xin lỗi, tôi không thể trả lời lúc này. Vui lòng thử lại sau."
                    await self.zalo_service.send_message(user_id, fallback_message)
                    return {
                        "status": "error",
                        "action": "chatbot_failed",
                        "user_id": user_id,
                        "message": "Chatbot service unavailable"
                    }
            else:
                logger.warning("Chatbot service not configured")
                return {
                    "status": "success",
                    "action": "message_received",
                    "note": "Chatbot not configured"
                }
        
        except Exception as e:
            logger.error(f"Error handling text message: {str(e)}")
            raise
    
    async def handle_image_message(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle image uploads"""
        try:
            message = event_data.get("message", {})
            user_id = event_data.get("sender", {}).get("id")
            
            logger.info(f"Received image from {user_id} - Images are not processed")
            
            await self.zalo_service.send_message(
                user_id,
                "📸 Hệ thống hiện tại chưa hỗ trợ xử lý ảnh.\n\n" +
                "Vui lòng gửi:\n" +
                "- File PDF cho CV\n" +
                "- File Excel/PDF cho WBS"
            )
            
            return {
                "status": "ignored",
                "action": "image_not_supported",
                "user_id": user_id
            }
        
        except Exception as e:
            logger.error(f"Error handling image message: {str(e)}")
            raise
    
    async def handle_file_message(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file uploads (CV PDFs, WBS files)"""
        try:
            message = event_data.get("message", {})
            attachments = message.get("attachments", [])
            user_id = event_data.get("sender", {}).get("id")
            
            # Determine user role
            user_role = self._get_user_role(user_id)
            logger.info(f"📎 File received from {user_id} (role: {user_role})")
            
            # Store that user sent an attachment
            self._recent_messages_with_attachments[user_id] = {
                'type': 'file',
                'timestamp': datetime.now()
            }
            
            for attachment in attachments:
                if attachment.get("type") == "file":
                    file_url = attachment.get("payload", {}).get("url")
                    file_name = attachment.get("payload", {}).get("name", "file")
                    file_size = attachment.get("payload", {}).get("size", 0)
                    
                    logger.info(f"Processing file: {file_name} ({file_size} bytes)")
                    
                    # Detect file type based on name and role
                    file_type = self._detect_file_type(file_name, user_role)
                    
                    # Handle CV file
                    if file_type == 'cv':
                        return await self._handle_cv_file(file_url, file_name, user_id, user_role)
                    
                    # Handle WBS file
                    elif file_type == 'wbs':
                        return await self._handle_wbs_file(file_url, file_name, user_id, user_role)
                    
                    # Unknown file type
                    else:
                        await self._send_file_type_error(user_id, file_name, user_role)
                        return {
                            "status": "error",
                            "message": "Unknown file type",
                            "file_name": file_name,
                            "user_role": user_role
                        }
            
            return {"status": "error", "message": "No valid file found"}
        
        except Exception as e:
            logger.error(f"Error handling file message: {str(e)}")
            raise
    
    async def _handle_cv_file(
        self, 
        file_url: str, 
        file_name: str, 
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Handle CV file processing"""
        try:
            # Only HR and unknown users can submit CV
            if user_role not in ['hr', 'unknown']:
                await self.zalo_service.send_message(
                    user_id,
                    "❌ Bạn không thể gửi CV.\n\nChỉ ứng viên mới có thể gửi CV để đăng ký."
                )
                return {
                    "status": "error",
                    "message": "User not allowed to submit CV",
                    "user_role": user_role
                }
            
            # Check if file is PDF
            if not file_name.lower().endswith('.pdf'):
                await self.zalo_service.send_message(
                    user_id,
                    f"⚠️ File '{file_name}' không phải là PDF.\n\n" +
                    "Vui lòng gửi CV dưới dạng file PDF."
                )
                return {
                    "status": "error",
                    "message": "CV must be PDF",
                    "file_name": file_name
                }
            
            # Download CV
            cv_path = await self._download_and_save_file(
                file_url, 
                user_id, 
                file_name,
                self.cv_dir
            )
            
            # Extract CV information
            cv_data = await self.extract_cv_information(cv_path)
            
            logger.info(f"✅ CV processed for user {user_id}")
            
            return {
                "status": "success",
                "action": "cv_received",
                "user_id": user_id,
                "cv_path": str(cv_path),
                "cv_data": cv_data
            }
            
        except Exception as e:
            logger.error(f"Error handling CV file: {str(e)}")
            await self.zalo_service.send_message(
                user_id,
                "❌ Lỗi xử lý CV. Vui lòng thử lại sau."
            )
            raise
    
    async def _handle_wbs_file(
        self, 
        file_url: str, 
        file_name: str, 
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Handle WBS file processing"""
        try:
            # Only managers can submit WBS
            if user_role != 'manager':
                await self.zalo_service.send_message(
                    user_id,
                    "❌ Bạn không có quyền gửi WBS.\n\n" +
                    "Chỉ Manager mới có thể tạo WBS cho dự án."
                )
                return {
                    "status": "error",
                    "message": "User not allowed to submit WBS",
                    "user_role": user_role
                }
            
            # Download WBS file
            wbs_path = await self._download_and_save_file(
                file_url,
                user_id,
                file_name,
                self.wbs_dir
            )
            
            # Read file content using utils function
            wbs_content = read_file_content(str(wbs_path))
            
            # Check if reading was successful
            if isinstance(wbs_content, str) and wbs_content.startswith("[ERROR]"):
                logger.error(f"Failed to read WBS file: {wbs_content}")
                await self.zalo_service.send_message(
                    user_id,
                    f"❌ Không thể đọc file WBS.\n\n{wbs_content}"
                )
                return {
                    "status": "error",
                    "message": "Failed to read WBS file",
                    "error": wbs_content
                }
            
            # Send to chatbot with file content (query = None for file processing)
            if self.chatbot_service:
                logger.info(f"📤 Sending WBS to chatbot for processing")
                
                chatbot_response = await self.chatbot_service.send_query_with_file(
                    user_id=user_id,
                    query=None,  # None to indicate file-only processing
                    file_content=wbs_content,
                    file_name=file_name
                )
                
                if chatbot_response:
                    await self.zalo_service.send_message(user_id, chatbot_response)
                    
                    logger.info(f"✅ WBS processed for manager {user_id}")
                    
                    return {
                        "status": "success",
                        "action": "wbs_received",
                        "user_id": user_id,
                        "wbs_path": str(wbs_path),
                        "chatbot_response": chatbot_response
                    }
                else:
                    await self.zalo_service.send_message(
                        user_id,
                        "❌ Không thể xử lý WBS lúc này.\n\nVui lòng thử lại sau."
                    )
                    return {
                        "status": "error",
                        "message": "Chatbot processing failed"
                    }
            else:
                await self.zalo_service.send_message(
                    user_id,
                    "❌ Hệ thống xử lý WBS chưa sẵn sàng."
                )
                return {
                    "status": "error",
                    "message": "Chatbot service not configured"
                }
                
        except Exception as e:
            logger.error(f"Error handling WBS file: {str(e)}")
            await self.zalo_service.send_message(
                user_id,
                "❌ Lỗi xử lý WBS. Vui lòng thử lại sau."
            )
            raise
    
    async def _send_file_type_error(self, user_id: str, file_name: str, user_role: str):
        """Send error message for unknown file type"""
        if user_role == 'hr' or user_role == 'unknown':
            message = f"""❌ File '{file_name}' không được hỗ trợ.

📄 **Để đăng ký làm nhân viên:**
- Tên file phải chứa: CV, Resume, Curriculum
- Định dạng: PDF
- Ví dụ: CV_NguyenVanA.pdf, Resume.pdf

Hoặc gõ "Đăng ký" để được hướng dẫn."""
        
        elif user_role == 'manager':
            message = f"""❌ File '{file_name}' không được hỗ trợ.

📊 **Để tạo WBS cho dự án:**
- Tên file phải chứa: WBS, Work-Breakdown, Project-Plan
- Định dạng: Excel (.xlsx), PDF, CSV
- Ví dụ: WBS_Project.xlsx, Work-Breakdown-Structure.pdf

File WBS sẽ được phân tích tự động để tạo tasks."""
        
        else:
            message = f"""❌ File '{file_name}' không được hỗ trợ.

**Loại file được phép:**
- 📄 CV (PDF) - Dành cho ứng viên
- 📊 WBS (Excel/PDF) - Dành cho Manager"""
        
        await self.zalo_service.send_message(user_id, message)
    
    async def _download_and_save_file(
        self, 
        file_url: str, 
        user_id: str, 
        file_name: str,
        target_dir: Path
    ) -> Path:
        """Download file and save to disk"""
        try:
            # Use ZaloService to download
            file_content = await self.zalo_service.download_file(file_url)
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{user_id}_{timestamp}_{file_name}"
            file_path = target_dir / safe_filename
            
            # Save file
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            logger.info(f"✅ File saved: {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"Error downloading and saving file: {str(e)}")
            raise
    
    async def _read_file_as_string(self, file_path: Path) -> str:
        """Read file content and convert to string"""
        try:
            file_ext = file_path.suffix.lower()
            
            # Handle PDF
            if file_ext == '.pdf':
                import PyPDF2
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            
            # Handle Excel
            elif file_ext in ['.xlsx', '.xls']:
                import pandas as pd
                df = pd.read_excel(file_path)
                return df.to_string()
            
            # Handle CSV
            elif file_ext == '.csv':
                import pandas as pd
                df = pd.read_csv(file_path)
                return df.to_string()
            
            # Handle text files
            elif file_ext in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            else:
                logger.warning(f"Unsupported file type: {file_ext}")
                return f"[File type {file_ext} not supported for text extraction]"
                
        except Exception as e:
            logger.error(f"Error reading file as string: {str(e)}")
            raise
    
    async def handle_follow_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle when user follows the OA"""
        try:
            user_id = event_data.get("follower", {}).get("id")
            await self.send_welcome_message(user_id)
            
            return {
                "status": "success",
                "action": "user_followed",
                "user_id": user_id
            }
        
        except Exception as e:
            logger.error(f"Error handling follow event: {str(e)}")
            raise
    
    async def _download_and_save_cv(self, file_url: str, user_id: str, file_name: str) -> Path:
        """Download CV file and save to disk"""
        try:
            # Use ZaloService to download
            file_content = await self.zalo_service.download_file(file_url)
            
            # Save file
            cv_filename = f"{user_id}_{file_name}"
            cv_path = self.upload_dir / cv_filename
            
            with open(cv_path, "wb") as f:
                f.write(file_content)
            
            logger.info(f"CV saved: {cv_path}")
            return cv_path
        
        except Exception as e:
            logger.error(f"Error downloading and saving CV: {str(e)}")
            raise
    
    async def extract_cv_information(self, cv_path: Path) -> Dict[str, Any]:
        """Extract information from CV PDF"""
        if not self.cv_analyzer:
            logger.error("CV analyzer not configured")
            return self._get_default_cv_data("CV analyzer not configured")
        
        try:
            cv_path_str = str(cv_path)
            if cv_path_str in self._cv_cache:
                logger.info(f"Using cached CV data for: {cv_path}")
                return self._cv_cache[cv_path_str]
            
            logger.info(f"Extracting CV information from: {cv_path}")
            result = self.cv_analyzer.query(cv_path_str)
            
            if not result or not result.candidates:
                logger.error("No candidate data extracted from CV")
                return self._get_default_cv_data("CV extraction failed")
            
            candidate = result.candidates[0]
            
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
    
    # ========== Registration Management ==========
    
    def store_pending_registration(
        self,
        cv_data: Dict[str, Any],
        cv_path: str,
        user_id_zalo: str
    ) -> str:
        """Store pending registration"""
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
        """Remove pending registration"""
        if registration_id in self._pending_registrations:
            del self._pending_registrations[registration_id]
            logger.info(f"Removed pending registration: {registration_id}")
    
    # ========== Message Senders (using ZaloService) ==========
    
    async def send_registration_instructions(self, user_id: str) -> bool:
        """Send registration instructions"""
        message = """Chào bạn! 👋

Để đăng ký làm nhân viên, vui lòng gửi CV của bạn dưới dạng file PDF.

📄 Yêu cầu CV bao gồm:
- ✅ File định dạng PDF
- ✅ Họ tên đầy đủ
- ✅ Email liên hệ
- ✅ Số điện thoại
- ✅ Kỹ năng và kinh nghiệm

Hệ thống sẽ tự động xử lý và thông báo kết quả cho bạn."""
        
        return await self.zalo_service.send_message(user_id, message)
    
    async def send_welcome_message(self, user_id: str) -> bool:
        """Send welcome message"""
        message = """Chào mừng bạn đến với Auto Project Manager! 🎉

Để đăng ký làm nhân viên, hãy gửi tin nhắn: "Đăng ký"

Chúng tôi sẽ hướng dẫn bạn các bước tiếp theo."""
        
        return await self.zalo_service.send_message(user_id, message)
    
    async def send_pending_notification(self, user_id: str, name: str) -> bool:
        """Notify candidate that CV is pending review"""
        message = f"""📄 CV ĐÃ ĐƯỢC GỬI THÀNH CÔNG!

Xin chào {name},

CV của bạn đã được hệ thống tiếp nhận và đang chờ HR xem xét.

⏳ Trạng thái: Đang chờ duyệt
📧 Chúng tôi sẽ thông báo kết quả cho bạn sớm nhất.

Cảm ơn bạn đã quan tâm!"""
        
        return await self.zalo_service.send_message(user_id, message)
    
    async def notify_hr(self, registration_id: str, user_data: Dict[str, Any]) -> bool:
        """Send notification to HR"""
        skills_text = ', '.join(user_data.get('skills', [])) if user_data.get('skills') else 'N/A'
        phone = user_data.get('phone', 'N/A')
        
        projects_text = ""
        projects = user_data.get('projects', [])
        if projects:
            for i, project in enumerate(projects[:3], 1):
                projects_text += f"\n  {i}. {project.get('name', 'N/A')} - {project.get('role', 'N/A')}"
        else:
            projects_text = "\n  Không có dự án"
        
        strengths = user_data.get('strengths', [])
        strengths_text = ', '.join(strengths) if strengths else 'N/A'
        
        message = f"""🆕 ĐƠN ĐĂNG KÝ MỚI CẦN DUYỆT

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
        
        return await self.zalo_service.send_message(self.hr_user_id, message)
    
    async def send_approval_notification(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Send approval notification to candidate"""
        phone_text = f"\n📱 SĐT: {user_data.get('phone')}" if user_data.get('phone') else ""
        
        message = f"""✅ ĐƠN ĐĂNG KÝ ĐÃ ĐƯỢC DUYỆT!

Chúc mừng {user_data.get('name')}!
Đơn đăng ký của bạn đã được HR phê duyệt.

📋 Thông tin tài khoản:
👤 Tên: {user_data.get('name')}
📧 Email: {user_data.get('email')}{phone_text}
🆔 ID: {user_data.get('id')}

HR sẽ liên hệ với bạn trong thời gian sớm nhất.
Cảm ơn bạn đã đăng ký!"""
        
        return await self.zalo_service.send_message(user_id, message)
    
    async def send_rejection_notification(self, user_id: str, name: str) -> bool:
        """Send rejection notification"""
        message = f"""❌ THÔNG BÁO TỪ HR

Xin chào {name},

Rất tiếc, đơn đăng ký của bạn chưa được chấp nhận lúc này.

Chúng tôi đã xem xét hồ sơ của bạn nhưng hiện tại vị trí chưa phù hợp.

Cảm ơn bạn đã quan tâm. Chúc bạn thành công!"""
        
        return await self.zalo_service.send_message(user_id, message)