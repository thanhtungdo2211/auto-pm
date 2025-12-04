from fastapi import APIRouter, HTTPException, BackgroundTasks
import logging
from datetime import datetime, timedelta
from typing import Dict
import requests
from typing import Optional

from services.zalo_service import ZaloService
from services.zalo_webhook_service import ZaloWebhookService
from services.chatbot_agent_service import ChatbotAgentService
from services.analysis_cv import GenCVAnalyzer
from services.report_handler import ReportHandler
from services.query_today_task import main as query_today_tasks
from dotenv import load_dotenv
import os

router = APIRouter(
    prefix="/api/zalo",
    tags=["zalo"]
)

logger = logging.getLogger(__name__)

zalo_service = ZaloService()
cv_analyzer = GenCVAnalyzer()
chatbot_service = ChatbotAgentService()
report_handler = ReportHandler()

zalo_webhook_service = ZaloWebhookService(
    zalo_service=zalo_service,
    cv_analyzer=cv_analyzer,
    chatbot_service=chatbot_service
)

# Cache for processed events to prevent duplicates
processed_events: Dict[str, datetime] = {}

# Load .env from project root (or environment)
load_dotenv()

PLANE_API_URL = os.getenv(
    "PLANE_API_URL",
    "https://e6b5c063c2c1.ngrok-free.app"  # fallback for local dev
)
PLANE_API_KEY = os.getenv(
    "PLANE_API_KEY",
    "plane_api_fe15a1874a304088b027ce4bbe8afc23"  # fallback for local dev
)
WORKSPACE_SLUG = os.getenv("WORKSPACE_SLUG", "workspace-mq")

# async def create_plane_user_and_add_to_workspace(
#     email: str,
#     first_name: str,
#     last_name: str,
#     username: Optional[str] = None,
#     role: int = 20  # Default role for workspace member
# ) -> dict:
#     """
#     Create user in Plane and add to workspace
    
#     Args:
#         email: User email
#         first_name: User first name
#         last_name: User last name
#         username: Username (defaults to email prefix)
#         role: Workspace role (20 = member)
    
#     Returns:
#         dict with user_created, member_added status
#     """
#     result = {
#         "user_created": False,
#         "member_added": False,
#         "user_data": None,
#         "member_data": None,
#         "errors": []
#     }
    
#     # Generate username from email if not provided
#     if not username:
#         username = email.split('@')[0]
    
#     # Step 1: Create user
#     try:
#         user_payload = {
#             "email": email,
#             "username": username,
#             "first_name": first_name,
#             "last_name": last_name,
#             "password": f"TempPass_{username}123!"  # Generate temporary password
#         }
        
#         logger.info(f"📤 Creating Plane user: {email}")
        
#         user_response = requests.post(
#             f"{PLANE_API_URL}/api/users/",
#             headers={"Content-Type": "application/json"},
#             json=user_payload,
#             timeout=10
#         )
        
#         if user_response.status_code in [200, 201]:
#             result["user_created"] = True
#             result["user_data"] = user_response.json()
#             logger.info(f"✅ Plane user created: {email}")
#         else:
#             error_msg = f"Failed to create user: {user_response.status_code} - {user_response.text}"
#             result["errors"].append(error_msg)
#             logger.error(f"❌ {error_msg}")
#             return result  # Stop here if user creation fails
    
#     except requests.exceptions.RequestException as e:
#         error_msg = f"Error creating user: {str(e)}"
#         result["errors"].append(error_msg)
#         logger.error(f"❌ {error_msg}")
#         return result
    
#     # Step 2: Add user to workspace
#     try:
#         member_payload = {
#             "email": email,
#             "role": role
#         }
        
#         logger.info(f"📤 Adding user to workspace: {WORKSPACE_SLUG}")
        
#         member_response = requests.post(
#             f"{PLANE_API_URL}/api/workspaces/{WORKSPACE_SLUG}/add-member/",
#             headers={
#                 "Content-Type": "application/json",
#                 "x-api-key": PLANE_API_KEY
#             },
#             json=member_payload,
#             timeout=10
#         )
        
#         if member_response.status_code in [200, 201]:
#             result["member_added"] = True
#             result["member_data"] = member_response.json()
#             logger.info(f"✅ User added to workspace: {WORKSPACE_SLUG}")
#         else:
#             error_msg = f"Failed to add member: {member_response.status_code} - {member_response.text}"
#             result["errors"].append(error_msg)
#             logger.error(f"❌ {error_msg}")
    
#     except requests.exceptions.RequestException as e:
#         error_msg = f"Error adding member to workspace: {str(e)}"
#         result["errors"].append(error_msg)
#         logger.error(f"❌ {error_msg}")
    
#     return result

def cleanup_old_events():
    """Remove events older than 1 hour"""
    cutoff = datetime.now() - timedelta(hours=1)
    to_remove = [
        event_id for event_id, timestamp in processed_events.items()
        if timestamp < cutoff
    ]
    for event_id in to_remove:
        del processed_events[event_id]


def generate_event_id(request: dict) -> str:
    """Generate unique event ID from request"""
    event_name = request.get('event_name', '')
    timestamp = request.get('timestamp', '')
    sender_id = request.get('sender', {}).get('id', '')
    msg_id = request.get('message', {}).get('msg_id', '')
    
    # Use msg_id if available for better uniqueness
    if msg_id:
        return f"{event_name}_{msg_id}_{sender_id}"
    return f"{event_name}_{timestamp}_{sender_id}"


async def process_webhook_async(request: dict, event_id: str):
    """
    Process webhook asynchronously
    This runs in the background after returning 200 to Zalo
    """
    try:
        result = await zalo_webhook_service.handle_webhook_event(request)
        
        # Handle daily report submission
        if result.get("action") == "daily_report_received":
            user_id = result.get("user_id")
            report_text = result.get("report_text")
            
            logger.info(f"📝 Processing daily report from user {user_id}")
            
            # Get user's tasks for today
            all_users_tasks = await query_today_tasks()
            
            # Find this user's tasks
            user_tasks = None
            for user_data in all_users_tasks:
                if str(user_data.get("zalo_user_id")) == str(user_id):
                    user_tasks = user_data.get("tasks", [])
                    break
            
            if not user_tasks:
                await zalo_service.send_message(
                    user_id,
                    "⚠️ Không tìm thấy task nào được gán cho bạn hôm nay."
                )
                return
            
            # Process the report
            process_result = await report_handler.process_staff_report(
                zalo_user_id=user_id,
                report_text=report_text,
                user_tasks=user_tasks
            )
            
            # Send response to user
            await zalo_service.send_message(
                user_id,
                process_result.get("message")
            )
            
            logger.info(f"✅ Daily report processed. Saved: {process_result.get('saved_count', 0)}, Failed: {process_result.get('failed_count', 0)}")
            return

        # Handle CV submission
        if result.get("action") == "cv_received":
            cv_data = result.get("cv_data", {})
            user_id_zalo = result.get("user_id")
            cv_path = result.get("cv_path")
            
            # Store pending registration
            registration_id = zalo_webhook_service.store_pending_registration(
                cv_data=cv_data,
                cv_path=cv_path,
                user_id_zalo=user_id_zalo
            )
            
            # Notify candidate that CV is pending
            await zalo_webhook_service.send_pending_notification(
                user_id_zalo,
                cv_data.get("name", "Unknown")
            )
            
            # Send to HR for approval
            await zalo_webhook_service.notify_hr(registration_id, cv_data)
            
            logger.info(f"✅ CV submitted and pending HR approval: {registration_id}")
        
        # Handle HR approval
        elif result.get("action") == "hr_approved":
            registration_id = result.get("registration_id")
            
            # Get pending registration
            pending = zalo_webhook_service.get_pending_registration(registration_id)
            
            if not pending:
                await zalo_service.send_message(
                    zalo_webhook_service.hr_user_id,
                    f"❌ Registration ID không tồn tại: {registration_id}"
                )
                return
            
            cv_data = pending["cv_data"]
            user_id_zalo = pending["user_id_zalo"]
            
            # Create user via Plane API
            try:
                # Prepare user data for Plane API
                name_parts = cv_data.get("name", "User").split()
                first_name = name_parts[0] if name_parts else "User"
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                email = cv_data.get("email")
                username = email.split('@')[0] if email else f"user_{user_id_zalo}"
                
                plane_payload = {
                    "email": email,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "password": f"TempPass_{username}123!",
                    "zalo_metadata": {
                        "name": cv_data.get("name", "Unknown"),
                        "phone": cv_data.get("phone"),
                        "zalo_user_id": user_id_zalo,
                        "description": cv_data.get("description", ""),
                        "skills": cv_data.get("skills", []),
                        "role": "staff",
                        "cv": pending["cv_path"],
                        "cv_data": cv_data,
                        "additional_info": cv_data.get("additional_info", {})
                    }
                }
                
                logger.info(f"📤 Creating Plane user: {email}")
                
                user_response = requests.post(
                    f"{PLANE_API_URL}/api/users/",
                    headers={"Content-Type": "application/json"},
                    json=plane_payload,
                    timeout=10
                )
                
                if user_response.status_code in [200, 201]:
                    user_data = user_response.json()
                    logger.info(f"✅ Plane user created: {email}")
                    
                    # Step 2: Add user to workspace
                    try:
                        member_payload = {
                            "email": email,
                            "role": 15  # Member role
                        }
                        
                        logger.info(f"📤 Adding user to workspace: {WORKSPACE_SLUG}")
                        
                        member_response = requests.post(
                            f"{PLANE_API_URL}/api/workspaces/{WORKSPACE_SLUG}/add-member/",
                            headers={
                                "Content-Type": "application/json",
                                "x-api-key": PLANE_API_KEY
                            },
                            json=member_payload,
                            timeout=10
                        )
                        
                        if member_response.status_code in [200, 201]:
                            logger.info(f"✅ User added to workspace: {WORKSPACE_SLUG}")
                        else:
                            error_msg = f"Failed to add member to workspace: {member_response.status_code} - {member_response.text}"
                            logger.error(f"❌ {error_msg}")
                            # Continue anyway - user is created
                    
                    except requests.exceptions.RequestException as e:
                        logger.error(f"❌ Error adding member to workspace: {str(e)}")
                        # Continue anyway - user is created
                    
                    # Remove pending registration
                    zalo_webhook_service.remove_pending_registration(registration_id)
                    
                    # Send approval notification to candidate
                    await zalo_webhook_service.send_approval_notification(
                        user_id_zalo,
                        {
                            "id": user_data.get("id"),
                            "name": cv_data.get("name"),
                            "email": email,
                            "phone": cv_data.get("phone"),
                            "skills": cv_data.get("skills", []),
                            "experience_years": cv_data.get("experience_years"),
                            "experience_level": cv_data.get("experience_level")
                        }
                    )
                    
                    # Confirm to HR
                    await zalo_service.send_message(
                        zalo_webhook_service.hr_user_id,
                        f"✅ Đã tạo tài khoản Plane cho {cv_data.get('name')}\n📧 Email: {email}\n📱 SĐT: {cv_data.get('phone')}\n🆔 User ID: {user_data.get('id')}"
                    )
                    
                    logger.info(f"✅ User approved and created: {user_data.get('id')}")
                
                else:
                    error_msg = f"Failed to create user: {user_response.status_code} - {user_response.text}"
                    logger.error(f"❌ {error_msg}")
                    await zalo_service.send_message(
                        zalo_webhook_service.hr_user_id,
                        f"❌ Lỗi tạo tài khoản Plane: {error_msg}"
                    )
                
            except Exception as e:
                logger.error(f"❌ User creation error: {str(e)}")
                await zalo_service.send_message(
                    zalo_webhook_service.hr_user_id,
                    f"❌ Lỗi tạo tài khoản: {str(e)}"
                )
        
        # Handle HR decline
        elif result.get("action") == "hr_declined":
            registration_id = result.get("registration_id")
            
            # Get pending registration
            pending = zalo_webhook_service.get_pending_registration(registration_id)
            
            if not pending:
                await zalo_service.send_message(
                    zalo_webhook_service.hr_user_id,
                    f"❌ Registration ID không tồn tại: {registration_id}"
                )
                return
            
            cv_data = pending["cv_data"]
            user_id_zalo = pending["user_id_zalo"]
            
            # Remove pending registration
            zalo_webhook_service.remove_pending_registration(registration_id)
            
            # Send rejection notification to candidate
            await zalo_webhook_service.send_rejection_notification(
                user_id_zalo,
                cv_data.get("name", "Unknown")
            )
            
            # Confirm to HR
            await zalo_service.send_message(
                zalo_webhook_service.hr_user_id,
                f"✅ Đã từ chối đơn của {cv_data.get('name')}"
            )
            
            logger.info(f"✅ Registration declined: {registration_id}")
        
        # Chatbot responses are already handled in handle_text_message
        logger.info(f"✅ Webhook processed successfully: {event_id}")
    
    except Exception as e:
        logger.error(f"❌ Error processing webhook async: {str(e)}", exc_info=True)


@router.post("/webhook")
async def zalo_webhook(request: dict, background_tasks: BackgroundTasks):
    """
    Handle Zalo webhook events
    Returns 200 immediately and processes in background
    """
    try:
        # Cleanup old events
        cleanup_old_events()
        
        # Generate unique event ID
        event_id = generate_event_id(request)
        
        # Check if already processed (duplicate prevention)
        if event_id in processed_events:
            logger.info(f"⚠️ Duplicate event ignored: {event_id}")
            return {"status": "ok", "message": "Event already processed"}
        
        # Mark event as being processed immediately
        processed_events[event_id] = datetime.now()
        
        # Log the event
        event_name = request.get('event_name', 'unknown')
        sender_id = request.get('sender', {}).get('id', 'unknown')
        logger.info(f"📥 Webhook received: {event_name} from {sender_id} | Event ID: {event_id}")
        
        # Add background task for async processing
        background_tasks.add_task(process_webhook_async, request, event_id)
        
        # Return 200 immediately to prevent Zalo timeout
        return {"status": "ok", "event_id": event_id}
    
    except Exception as e:
        logger.error(f"❌ Error in webhook handler: {str(e)}", exc_info=True)
        # Still return 200 to prevent retries
        return {"status": "error", "message": "Internal error, will not retry"}


@router.get("/conversation/{zalo_user_id}")
async def get_conversation(zalo_user_id: str, count: int = 10, offset: int = 0):
    """Get conversation history with a user"""
    try:
        conversation = await zalo_service.get_conversation(zalo_user_id, count, offset)
        return {
            "status": "success",
            "user_id": zalo_user_id,
            "conversation": conversation
        }
    except Exception as e:
        logger.error(f"❌ Error retrieving conversation for user {zalo_user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/pending-registrations")
async def get_pending_registrations():
    """Get all pending registrations for HR dashboard"""
    try:
        pending = zalo_webhook_service._pending_registrations
        
        return {
            "status": "success",
            "count": len(pending),
            "registrations": [
                {
                    "registration_id": reg_id,
                    "name": data["cv_data"].get("name"),
                    "email": data["cv_data"].get("email"),
                    "phone": data["cv_data"].get("phone"),
                    "role": data["cv_data"].get("role"),
                    "experience_years": data["cv_data"].get("experience_years"),
                    "experience_level": data["cv_data"].get("experience_level"),
                    "skills": data["cv_data"].get("skills"),
                    "timestamp": data["timestamp"]
                }
                for reg_id, data in pending.items()
            ]
        }
    except Exception as e:
        logger.error(f"❌ Error getting pending registrations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve/{registration_id}")
async def approve_registration(registration_id: str):
    """Approve a pending registration (alternative to Zalo message)"""
    try:
        pending = zalo_webhook_service.get_pending_registration(registration_id)
        
        if not pending:
            raise HTTPException(status_code=404, detail="Registration not found")
        
        cv_data = pending["cv_data"]
        user_id_zalo = pending["user_id_zalo"]
        
        # Prepare user data for Plane API
        name_parts = cv_data.get("name", "User").split()
        first_name = name_parts[0] if name_parts else "User"
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        email = cv_data.get("email")
        username = email.split('@')[0] if email else f"user_{user_id_zalo}"
        
        plane_payload = {
            "email": email,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "password": f"TempPass_{username}123!",
            "zalo_metadata": {
                "name": cv_data.get("name", "Unknown"),
                "phone": cv_data.get("phone"),
                "zalo_user_id": user_id_zalo,
                "description": cv_data.get("description", ""),
                "skills": cv_data.get("skills", []),
                "role": "staff",
                "cv": pending["cv_path"],
                "cv_data": cv_data,
                "additional_info": cv_data.get("additional_info", {})
            }
        }
        
        # Create user via Plane API
        user_response = requests.post(
            f"{PLANE_API_URL}/api/users/",
            headers={"Content-Type": "application/json"},
            json=plane_payload,
            timeout=10
        )
        
        if user_response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create Plane user: {user_response.text}"
            )
        
        user_data = user_response.json()
        
        # Remove pending registration
        zalo_webhook_service.remove_pending_registration(registration_id)
        
        # Send notifications
        await zalo_webhook_service.send_approval_notification(user_id_zalo, {
            "id": user_data.get("id"),
            "name": cv_data.get("name"),
            "email": email,
            "phone": cv_data.get("phone")
        })
        
        return {
            "status": "success",
            "message": "User approved and created in Plane",
            "user_id": user_data.get("id")
        }
        
    except Exception as e:
        logger.error(f"❌ Error approving registration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decline/{registration_id}")
async def decline_registration(registration_id: str):
    """Decline a pending registration (alternative to Zalo message)"""
    try:
        pending = zalo_webhook_service.get_pending_registration(registration_id)
        
        if not pending:
            raise HTTPException(status_code=404, detail="Registration not found")
        
        cv_data = pending["cv_data"]
        user_id_zalo = pending["user_id_zalo"]
        
        # Remove pending registration
        zalo_webhook_service.remove_pending_registration(registration_id)
        
        # Send notification
        await zalo_webhook_service.send_rejection_notification(
            user_id_zalo,
            cv_data.get("name", "Unknown")
        )
        
        return {
            "status": "success",
            "message": "Registration declined"
        }
        
    except Exception as e:
        logger.error(f"❌ Error declining registration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))