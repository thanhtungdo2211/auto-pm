from fastapi import APIRouter, HTTPException
import logging
from datetime import datetime, timedelta
from typing import Dict
from schemas import UserCreate
from services.zalo_service import ZaloService
from services.zalo_webhook_service import ZaloWebhookService
from services.project_service import ProjectService

router = APIRouter(
    prefix="/api/zalo",
    tags=["zalo"]
)

logger = logging.getLogger(__name__)

# Import global services (these should be injected via dependency injection in production)
# For now, we'll initialize them here
from services.analysis_cv import GenCVAnalyzer

zalo_service = ZaloService()
cv_analyzer = GenCVAnalyzer()
zalo_webhook_service = ZaloWebhookService(
    zalo_service=zalo_service,
    cv_analyzer=cv_analyzer
)
project_service = ProjectService()

# Cache for processed events
processed_events: Dict[str, datetime] = {}


def cleanup_old_events():
    """Remove events older than 1 hour"""
    cutoff = datetime.now() - timedelta(hours=1)
    to_remove = [
        event_id for event_id, timestamp in processed_events.items()
        if timestamp < cutoff
    ]
    for event_id in to_remove:
        del processed_events[event_id]


@router.post("/webhook")
async def zalo_webhook(request: dict):
    """Handle Zalo webhook events"""
    try:
        # Cleanup old events
        cleanup_old_events()
        
        # Create idempotency key from request
        event_id = f"{request.get('event_name', '')}_{request.get('timestamp', '')}_{request.get('sender', {}).get('id', '')}"
        
        # Check if already processed
        if event_id in processed_events:
            logger.info(f"Event already processed: {event_id}")
            return {"status": "duplicate", "message": "Event already processed"}
        
        result = await zalo_webhook_service.handle_webhook_event(request)
        
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
            
            # Mark event as processed
            processed_events[event_id] = datetime.now()
            
            logger.info(f"✅ CV submitted and pending HR approval: {registration_id}")
            return {
                "status": "success",
                "action": "pending_approval",
                "registration_id": registration_id
            }
        
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
                return {"status": "error", "message": "Registration not found"}
            
            cv_data = pending["cv_data"]
            user_id_zalo = pending["user_id_zalo"]
            
            # Create user with full CV data
            user_create_data = UserCreate(
                name=cv_data.get("name", "Unknown"),
                email=cv_data.get("email"),
                phone=cv_data.get("phone"),
                cv=pending["cv_path"],
                cv_data=cv_data,
                zalo_user_id=user_id_zalo,
                description=cv_data.get("description", ""),
                skills=cv_data.get("skills", []),
                role="staff"
            )
            
            try:
                user = project_service.create_user(user_create_data)
                
                # Remove pending registration
                zalo_webhook_service.remove_pending_registration(registration_id)
                
                # Mark event as processed
                processed_events[event_id] = datetime.now()
                
                # Send approval notification to candidate
                await zalo_webhook_service.send_approval_notification(
                    user_id_zalo,
                    {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "phone": user.phone,
                        "skills": user.skills,
                        "experience_years": cv_data.get("experience_years"),
                        "experience_level": cv_data.get("experience_level")
                    }
                )
                
                # Confirm to HR
                await zalo_service.send_message(
                    zalo_webhook_service.hr_user_id,
                    f"✅ Đã tạo tài khoản cho {user.name}\n📱 SĐT: {user.phone}\n🆔 User ID: {user.id}"
                )
                
                logger.info(f"✅ User approved and created: {user.id}")
                return {"status": "success", "user_id": user.id}
                
            except ValueError as e:
                logger.error(f"❌ User creation error: {str(e)}")
                await zalo_service.send_message(
                    zalo_webhook_service.hr_user_id,
                    f"❌ Lỗi tạo tài khoản: {str(e)}"
                )
                return {"status": "error", "message": str(e)}
        
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
                return {"status": "error", "message": "Registration not found"}
            
            cv_data = pending["cv_data"]
            user_id_zalo = pending["user_id_zalo"]
            
            # Remove pending registration
            zalo_webhook_service.remove_pending_registration(registration_id)
            
            # Mark event as processed
            processed_events[event_id] = datetime.now()
            
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
            return {"status": "success", "action": "declined"}
        
        return {"status": "success", "result": result}
    
    except Exception as e:
        logger.error(f"❌ Error processing Zalo webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
        
        # Create user
        user_create_data = UserCreate(
            name=cv_data.get("name", "Unknown"),
            email=cv_data.get("email"),
            phone=cv_data.get("phone"),
            cv=pending["cv_path"],
            cv_data=cv_data,
            zalo_user_id=user_id_zalo,
            description=cv_data.get("description", ""),
            skills=cv_data.get("skills", []),
            role="staff"
        )
        
        user = project_service.create_user(user_create_data)
        
        # Remove pending registration
        zalo_webhook_service.remove_pending_registration(registration_id)
        
        # Send notifications
        await zalo_webhook_service.send_approval_notification(user_id_zalo, {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone
        })
        
        return {
            "status": "success",
            "message": "User approved and created",
            "user_id": user.id
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
