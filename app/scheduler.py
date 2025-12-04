import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import your existing query function
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from services.query_today_task import main as query_today_tasks
from services.zalo_service import ZaloService
from zoneinfo import ZoneInfo

scheduler = AsyncIOScheduler()
zalo_service = ZaloService()

def format_task_message(user_data: dict) -> str:
    """Format user tasks into a readable message"""
    display_name = user_data.get('display_name', 'User')
    task_count = user_data.get('task_count', 0)
    tasks = user_data.get('tasks', [])
    
    if task_count == 0:
        return f"Chào {display_name}!\nBạn không có task nào hôm nay."
    
    # Build message
    message = f"Chào {display_name}!\n"
    message += f"Bạn có {task_count} task hôm nay:\n"
    message += "─" * 30 + "\n\n"
    
    for idx, task in enumerate(tasks, 1):
        project_name = task.get('project_name', 'N/A')
        issue = task.get('issue', {})
        task_name = issue.get('name', 'N/A')
        priority = issue.get('priority', 'none')
        target_date = issue.get('target_date', 'N/A')
        
        priority_text = {
            'urgent': 'URGENT',
            'high': 'HIGH',
            'medium': 'MEDIUM',
            'low': 'LOW',
            'none': 'NONE'
        }.get(priority, 'NONE')
        
        message += f"• {task_name}\n"
        message += f"  Priority: {priority_text}\n"
        message += f"  Project: {project_name}\n"
        message += f"  Due: {target_date}\n\n"
    
    message += "─" * 30 + "\n"
    message += "Chúc bạn làm việc hiệu quả!"
    
    return message

async def send_daily_task_notifications():
    """Query today's tasks and send notifications to users"""
    try:
        logger.info(f"Starting daily task notification job at {datetime.now()}")
        
        # Run the query_today_task script (now async)
        notification_data = await query_today_tasks()
        
        if not notification_data:
            logger.info("No users with tasks today")
            return
        
        # Send notifications to each user
        success_count = 0
        failed_count = 0

        for user in notification_data:
            zalo_user_id = user.get("zalo_user_id")
            
            if not zalo_user_id:
                logger.warning(f"No Zalo user ID for {user.get('email')} - skipping")
                failed_count += 1
                continue
            
            try:
                # Format message with user's tasks
                message = format_task_message(user)
                
                # Send via Zalo
                sent = await zalo_service.send_message(
                    user_id=str(zalo_user_id),
                    text=message,
                    metadata={
                        "type": "daily_task_notification",
                        "date": datetime.now().isoformat(),
                        "task_count": user.get("task_count", 0)
                    }
                )
                
                if sent:
                    logger.info(f"Notification sent to {user.get('display_name')} ({user.get('email')})")
                    success_count += 1
                else:
                    logger.error(f"Failed to send notification to {user.get('display_name')}")
                    failed_count += 1
                    
                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error sending notification to {user.get('email')}: {e}")
                failed_count += 1
        
        logger.info(f"Daily task notifications completed. Success: {success_count}, Failed: {failed_count}")
        
    except Exception as e:
        logger.error(f"Error in daily task notification job: {e}", exc_info=True)

async def send_daily_report_request():
    """Send report request to all staff at 6 PM"""
    try:
        logger.info(f"Starting daily report request job at {datetime.now()}")
        
        # Query all active users with tasks
        notification_data = await query_today_tasks()
        
        if not notification_data:
            logger.info("No users to send report request")
            return
        
        success_count = 0
        failed_count = 0
        
        for user in notification_data:
            zalo_user_id = user.get("zalo_user_id")
            
            if not zalo_user_id:
                logger.warning(f"No Zalo user ID for {user.get('email')} - skipping")
                failed_count += 1
                continue
            
            try:
                display_name = user.get('display_name', 'User')
                task_count = user.get('task_count', 0)
                
                message = f"Chào {display_name}!\n\n"
                message += f"Đã đến 6 giờ chiều, vui lòng gửi báo cáo công việc hôm nay.\n"
                message += f"Bạn có {task_count} task cần báo cáo.\n\n"
                message += "Hãy gửi báo cáo theo định dạng:\n"
                message += "• Task đã làm\n"
                message += "• Tiến độ (%)\n"
                message += "• Thời gian đã dùng\n"
                message += "• Ghi chú (nếu có)\n\n"
                message += "Ví dụ: Task A: 60%, 3 giờ. Task B: 100%, 4 giờ."
                
                sent = await zalo_service.send_message(
                    user_id=str(zalo_user_id),
                    text=message,
                    metadata={
                        "type": "daily_report_request",
                        "date": datetime.now().isoformat(),
                        "expecting_report": True
                    }
                )
                
                if sent:
                    logger.info(f"Report request sent to {display_name}")
                    success_count += 1
                else:
                    logger.error(f"Failed to send request to {display_name}")
                    failed_count += 1
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error sending request to {user.get('email')}: {e}")
                failed_count += 1
        
        logger.info(f"Report requests completed. Success: {success_count}, Failed: {failed_count}")
        
    except Exception as e:
        logger.error(f"Error in daily report request job: {e}", exc_info=True)


def start_scheduler():
    """
    Initialize and start the scheduler
    """
    asia_tz = ZoneInfo("Asia/Ho_Chi_Minh")

    # Daily task notifications at 8:00 AM
    scheduler.add_job(
        send_daily_task_notifications,
        trigger=CronTrigger(hour=8, minute=0, timezone=asia_tz),
        id="daily_task_notifications",
        name="Send daily task notifications at 08:00 Asia/Ho_Chi_Minh (GMT+7)",
        replace_existing=True
    )
    
    # Daily report request at 6:00 PM
    scheduler.add_job(
        send_daily_report_request,
        trigger=CronTrigger(hour=18, minute=0, timezone=asia_tz),
        id="daily_report_request",
        name="Send daily report request at 18:00 Asia/Ho_Chi_Minh (GMT+7)",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started. Jobs scheduled for 8:00 AM and 6:00 PM")

def shutdown_scheduler():
    """
    Shutdown the scheduler gracefully
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")