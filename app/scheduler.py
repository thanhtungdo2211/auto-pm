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
        return f"Chào {display_name}! 👋\nBạn không có task nào hôm nay."
    
    # Build message
    message = f"🔔 Chào {display_name}!\n"
    message += f"Bạn có {task_count} task hôm nay:\n"
    message += "─" * 30 + "\n\n"
    
    for idx, task in enumerate(tasks, 1):
        project_name = task.get('project_name', 'N/A')
        issue = task.get('issue', {})
        task_name = issue.get('name', 'N/A')
        priority = issue.get('priority', 'none')
        target_date = issue.get('target_date', 'N/A')
        
        priority_emoji = {
            'urgent': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢',
            'none': '⚪'
        }.get(priority, '⚪')
        
        message += f"{idx}. {priority_emoji} {task_name}\n"
        message += f"   📁 Project: {project_name}\n"
        message += f"   📅 Due: {target_date}\n\n"
    
    message += "─" * 30 + "\n"
    message += "💪 Chúc bạn làm việc hiệu quả!"
    
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
                    logger.info(f"✅ Notification sent to {user.get('display_name')} ({user.get('email')})")
                    success_count += 1
                else:
                    logger.error(f"❌ Failed to send notification to {user.get('display_name')}")
                    failed_count += 1
                    
                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error sending notification to {user.get('email')}: {e}")
                failed_count += 1
        
        logger.info(f"Daily task notifications completed. Success: {success_count}, Failed: {failed_count}")
        
    except Exception as e:
        logger.error(f"Error in daily task notification job: {e}", exc_info=True)


def start_scheduler():
    """
    Initialize and start the scheduler
    """

    # Schedule coroutines directly - AsyncIOScheduler handles them properly
    # now = datetime.now()
    # test_time = now + timedelta(minutes=1)

    # Schedule daily task notifications at 8:00 AM
    asia_tz = ZoneInfo("Asia/Ho_Chi_Minh")

    scheduler.add_job(
        send_daily_task_notifications,
        trigger=CronTrigger(hour=8, minute=0, timezone=asia_tz),
        id="daily_task_notifications",
        name="Send daily task notifications at 08:00 Asia/Ho_Chi_Minh (GMT+7)",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started. Daily task notifications scheduled for 8:00 AM")

def shutdown_scheduler():
    """
    Shutdown the scheduler gracefully
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")