import asyncio
import os
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta, date
import logging

logger = logging.getLogger(__name__)

# Import your existing query function
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from services.query_today_task import main as query_today_tasks
from services.zalo_service import ZaloService
from services.chatbot_agent_service import ChatbotAgentService
from zoneinfo import ZoneInfo
from services.manager_report_service import (
    send_manager_summary,
    _parse_manager_ids,
)
from services.previous_day_report_service import (
    aggregate_previous_day_reports,
    format_previous_day_report,
)
scheduler = AsyncIOScheduler()
zalo_service = ZaloService()
chatbot_service = ChatbotAgentService()


async def send_previous_day_manager_report(manager_ids=None):
    """
    Gửi báo cáo tổng hợp của ngày hôm trước cho danh sách manager (Zalo ID).
    """
    manager_ids = manager_ids or _parse_manager_ids(os.getenv("MANAGER_ZALO_IDS", ""))
    if not manager_ids:
        logger.warning("No manager IDs configured; skip previous-day report")
        return

    try:
        summary = await aggregate_previous_day_reports()
        # Gửi thẳng JSON summary cho chatbot (bỏ qua bước LLM viết lại)
        query_str = json.dumps(summary, ensure_ascii=False)

        sent = 0
        failed = 0
        for manager_id in manager_ids:
            try:
                logger.info(
                    "Chatbot request (manager summary): user=%s role=%s mode_report=%s query_json=%s",
                    manager_id,
                    "manager",
                    True,
                    query_str,
                )

                chat_res = await chatbot_service.send_chat_request(
                    user_id=str(manager_id),
                    role="manager",
                    query=query_str,
                    mode_report=True,
                    file_content="",
                )

                resp_mode = (chat_res or {}).get("mode_report", True)
                message = (chat_res or {}).get("response") or query_str

                ok = await zalo_service.send_message(
                    user_id=str(manager_id),
                    text=message,
                    metadata={
                        "type": "previous_day_report",
                        "day": summary.get("day"),
                        "mode_report": resp_mode,
                    },
                )
                if ok:
                    sent += 1
                else:
                    failed += 1
            except Exception as exc:  # pragma: no cover - network path
                logger.error(
                    "Error sending previous-day report to manager %s: %s",
                    manager_id,
                    exc,
                )
                failed += 1

        logger.info(
            "Previous-day report sent. Success: %s, Failed: %s, Day: %s",
            sent,
            failed,
            summary.get("day"),
        )
    except Exception as exc:  # pragma: no cover - network path
        logger.error("Failed to send previous-day manager report: %s", exc, exc_info=True)


async def send_manager_report_for_day(target_day: str | None = None, manager_ids=None):
    """
    Gửi báo cáo tổng hợp cho manager cho một ngày cụ thể (phục vụ test).
    Nếu không truyền target_day, mặc định là hôm nay.
    """
    manager_ids = manager_ids or _parse_manager_ids(os.getenv("MANAGER_ZALO_IDS", ""))
    if not manager_ids:
        logger.warning("No manager IDs configured; skip manager report custom day")
        return

    day = target_day or date.today().isoformat()
    try:
        summary = await aggregate_previous_day_reports(target_day=day)
        query_str = json.dumps(summary, ensure_ascii=False)

        sent = 0
        failed = 0
        for manager_id in manager_ids:
            try:
                logger.info(
                    "Chatbot request (manager summary custom day=%s): user=%s role=%s mode_report=%s query_json=%s",
                    day,
                    manager_id,
                    "manager",
                    True,
                    query_str,
                )

                chat_res = await chatbot_service.send_chat_request(
                    user_id=str(manager_id),
                    role="manager",
                    query=query_str,
                    mode_report=True,
                    file_content="",
                )

                resp_mode = (chat_res or {}).get("mode_report", True)
                message = (chat_res or {}).get("response") or query_str

                ok = await zalo_service.send_message(
                    user_id=str(manager_id),
                    text=message,
                    metadata={
                        "type": "manager_report_custom_day",
                        "day": summary.get("day"),
                        "mode_report": resp_mode,
                    },
                )
                if ok:
                    sent += 1
                else:
                    failed += 1
            except Exception as exc:  # pragma: no cover - network path
                logger.error(
                    "Error sending manager report (day=%s) to %s: %s",
                    day,
                    manager_id,
                    exc,
                )
                failed += 1

        logger.info(
            "Manager report (day=%s) sent. Success: %s, Failed: %s",
            summary.get("day"),
            sent,
            failed,
        )
    except Exception as exc:  # pragma: no cover - network path
        logger.error("Failed to send manager report (day=%s): %s", day, exc, exc_info=True)

def format_task_message(user_data: dict) -> str:
    """
    Format user tasks in the requested style for staff daily notification.
    """
    display_name = user_data.get("display_name", "Bạn")
    task_count = user_data.get("task_count", 0)
    tasks = user_data.get("tasks", [])

    if task_count == 0:
        return f"Chào {display_name}. Hôm nay bạn không có task nào."

    lines = [f"Chào {display_name}. Hôm nay, bạn có {task_count} tasks như sau:\n"]
    for idx, task in enumerate(tasks, 1):
        issue = task.get("issue", {})
        name = issue.get("name", "N/A")
        start_date = issue.get("start_date", "N/A")
        target_date = issue.get("target_date", "N/A")
        priority = issue.get("priority") or "none"
        priority_text = {
            "urgent": "Khẩn cấp",
            "high": "Cao",
            "medium": "Trung bình",
            "low": "Thấp",
            "none": "Không có",
        }.get(priority, "Không có")
        assignees = issue.get("assignees") or []
        assignee_count = len(assignees)

        lines.append(f"{idx}. {name}")
        lines.append("   - Trạng thái: Chưa hoàn thành")
        lines.append(f"   - Thời gian: {start_date} -> {target_date}")
        lines.append(f"   - Ưu tiên: {priority_text}")
        lines.append(f"   - Assignees: {assignee_count}\n")

    lines.append("Chúc bạn có một ngày làm việc vui vẻ và hiệu quả.")
    return "\n".join(lines)

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
                role = user.get("role") or "staff"
                # Format trực tiếp không qua chatbot
                message = format_task_message(user)
                
                # Send via Zalo
                sent = await zalo_service.send_message(
                    user_id=str(zalo_user_id),
                    text=message,
                    metadata={
                        "type": "daily_task_notification",
                        "date": datetime.now().isoformat(),
                        "task_count": user.get("task_count", 0),
                        "mode_report": False,
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
                role = user.get("role") or "staff"
                task_names = [t.get("issue", {}).get("name") for t in user.get("tasks", [])]
                task_names = [n for n in task_names if n]
                task_list_text = ", ".join(task_names[:5])
                if len(task_names) > 5:
                    task_list_text += f" (+{len(task_names) - 5} task khác)"

                # Gửi thẳng dữ liệu JSON (string) cho chatbot, bỏ qua LLM viết lại
                raw_payload = {
                    "user_id": str(zalo_user_id),
                    "role": role,
                    "display_name": display_name,
                    "task_count": task_count,
                    "tasks": user.get("tasks", []),
                    "task_names_preview": task_list_text,
                }
                query_str = json.dumps(raw_payload, ensure_ascii=False)

                logger.info(
                    "Chatbot request (staff report reminder): user=%s role=%s mode_report=%s query_json=%s",
                    zalo_user_id,
                    role,
                    True,
                    query_str,
                )

                chat_res = await chatbot_service.send_chat_request(
                    user_id=str(zalo_user_id),
                    role=role,
                    query=query_str,
                    mode_report=True,
                    file_content="",
                )

                resp_mode = (chat_res or {}).get("mode_report", True)
                message = (chat_res or {}).get("response")
                if not message:
                    # Fallback: gửi luôn JSON gốc
                    message = query_str
                
                sent = await zalo_service.send_message(
                    user_id=str(zalo_user_id),
                    text=message,
                    metadata={
                        "type": "daily_report_request",
                        "date": datetime.now().isoformat(),
                        "expecting_report": True,
                        "mode_report": resp_mode,
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


# def start_scheduler():
#     """
#     Initialize and start the scheduler
#     """
#     asia_tz = ZoneInfo("Asia/Ho_Chi_Minh")
#     manager_ids = _parse_manager_ids(os.getenv("MANAGER_ZALO_IDS", ""))
#     # Previous-day manager report at 8:00 AM
#     scheduler.add_job(
#         send_previous_day_manager_report,
#         trigger=CronTrigger(hour=8, minute=0, timezone=asia_tz),
#         kwargs={"manager_ids": manager_ids},
#         id="previous_day_manager_report",
#         name="Send previous-day report to managers at 08:00 Asia/Ho_Chi_Minh (GMT+7)",
#         replace_existing=True,
#     )
#     # Daily task notifications at 8:00 AM
#     scheduler.add_job(
#         send_daily_task_notifications,
#         trigger=CronTrigger(hour=10, minute=29, timezone=asia_tz),
#         id="daily_task_notifications",
#         name="Send daily task notifications at 08:00 Asia/Ho_Chi_Minh (GMT+7)",
#         replace_existing=True
#     )
    
#     # Daily report request at 6:00 PM
#     scheduler.add_job(
#         send_daily_report_request,
#         trigger=CronTrigger(hour=10, minute=30, timezone=asia_tz),
#         id="daily_report_request",
#         name="Send daily report request at 18:00 Asia/Ho_Chi_Minh (GMT+7)",
#         replace_existing=True
#     )

#     # Manager summary of yesterday's reports at 8:30 AM
#     scheduler.add_job(
#         send_manager_summary,
#         trigger=CronTrigger(hour=8, minute=30, timezone=asia_tz),
#         kwargs={"zalo_service": zalo_service, "manager_ids": manager_ids},
#         id="manager_yesterday_summary",
#         name="Send yesterday summary to managers at 08:30 Asia/Ho_Chi_Minh (GMT+7)",
#         replace_existing=True,
#     )
       
#     scheduler.start()
#     logger.info("Scheduler started. Jobs scheduled for 8:00 AM and 6:00 PM")

def shutdown_scheduler():
    """
    Shutdown the scheduler gracefully
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")


def list_scheduler_jobs():
    """
    Hàm test/tiện ích: trả về thông tin các job đang có trong scheduler.
    Dùng cho mục đích kiểm tra nhanh.
    """
    jobs_info = []
    for job in scheduler.get_jobs():
        jobs_info.append(
            {
                "id": job.id,
                "name": job.name,
                "trigger": str(job.trigger),
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "kwargs": job.kwargs,
            }
        )
    logger.info("Scheduler jobs: %s", jobs_info)
    return jobs_info


def add_test_jobs_to_scheduler():
    """
    Thêm 3 job test vào scheduler global:
    1) Gửi danh sách task cho staff (dùng LLM viết lại) — chạy sau 1 phút.
    2) Nhắc staff gửi báo cáo (gửi JSON thẳng) — chạy sau 2 phút.
    3) Tổng hợp báo cáo hôm trước gửi manager (gửi JSON thẳng) — chạy sau 3 phút.
    """
    asia_tz = ZoneInfo("Asia/Ho_Chi_Minh")
    now = datetime.now(asia_tz)
    t1 = now + timedelta(minutes=5)
    t2 = now + timedelta(minutes=5)
    t3 = now + timedelta(minutes=1)

    manager_ids = _parse_manager_ids(os.getenv("MANAGER_ZALO_IDS", ""))

    scheduler.add_job(
        send_daily_task_notifications,
        trigger=DateTrigger(run_date=t1),
        id="test_daily_task_notifications",
        name="Test - daily task notifications (t+1m)",
        replace_existing=True,
    )

    scheduler.add_job(
        send_daily_report_request,
        trigger=DateTrigger(run_date=t2),
        id="test_daily_report_request",
        name="Test - nhắc báo cáo staff (t+2m)",
        replace_existing=True,
    )

    scheduler.add_job(
        send_previous_day_manager_report,
        trigger=DateTrigger(run_date=t3),
        kwargs={"manager_ids": manager_ids},
        id="test_previous_day_manager_report",
        name="Test - tổng hợp gửi manager (t+3m)",
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()

    logger.info(
        "Added test jobs to scheduler at %s (t1=%s, t2=%s, t3=%s)",
        now.isoformat(),
        t1.isoformat(),
        t2.isoformat(),
        t3.isoformat(),
    )


def add_test_jobs_sequential():
    """
    Thêm 3 job test chạy lần lượt sau 1, 2, 5 phút tính từ thời điểm gọi:
    1) daily_task_notifications (LLM viết lại task cho staff) – t+1m
    2) daily_report_request (nhắc staff, gửi JSON thẳng) – t+2m
    3) manager_report_for_day với ngày hiện tại (gửi JSON thẳng) – t+5m
    """
    asia_tz = ZoneInfo("Asia/Ho_Chi_Minh")
    now = datetime.now(asia_tz)
    t1 = now + timedelta(minutes=1)
    t2 = now + timedelta(minutes=2)
    t3 = now + timedelta(minutes=5)

    manager_ids = _parse_manager_ids(os.getenv("MANAGER_ZALO_IDS", ""))

    scheduler.add_job(
        send_daily_task_notifications,
        trigger=DateTrigger(run_date=t1),
        id="test_seq_daily_task_notifications",
        name="Test seq - daily task notifications (t+1m)",
        replace_existing=True,
    )

    scheduler.add_job(
        send_daily_report_request,
        trigger=DateTrigger(run_date=t2),
        id="test_seq_daily_report_request",
        name="Test seq - nhắc báo cáo staff (t+3m)",
        replace_existing=True,
    )

    scheduler.add_job(
        send_manager_report_for_day,
        trigger=DateTrigger(run_date=t3),
        kwargs={"target_day": date.today().isoformat(), "manager_ids": manager_ids},
        id="test_seq_manager_report_today",
        name="Test seq - báo cáo manager (day=today, t+5m)",
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()

    logger.info(
        "Added sequential test jobs at %s (t1=%s, t2=%s, t3=%s)",
        now.isoformat(),
        t1.isoformat(),
        t2.isoformat(),
        t3.isoformat(),
    )


# async def main():
#     """
#     Hàm main cũ: chạy start_scheduler với cấu hình cron cố định.
#     Được giữ lại để tham khảo, đã comment theo yêu cầu.
#     """
#     start_scheduler()
#     await asyncio.Event().wait()


def start_scheduler():
    """
    Hàm main test: lên lịch nhanh để kiểm thử.
    - Nhắc báo cáo cuối ngày cho staff: chạy sau 1 phút kể từ hiện tại.
    - Tổng hợp báo cáo cho manager: chạy sau 5 phút kể từ hiện tại.
    """
    # Shutdown scheduler cũ nếu đang chạy để tránh duplicate jobs
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Shutdown existing scheduler before starting new one")
    
    asia_tz = ZoneInfo("Asia/Ho_Chi_Minh")
    now = datetime.now(asia_tz)
    staff_notify_time = now + timedelta(minutes=0)
    staff_report_time = now + timedelta(minutes=0)
    manager_report_time = now + timedelta(minutes=4)

    manager_ids = _parse_manager_ids(os.getenv("MANAGER_ZALO_IDS", ""))
    # Sử dụng scheduler global thay vì tạo mới
    scheduler.add_job(
        send_daily_task_notifications,
        trigger=DateTrigger(run_date=staff_notify_time),
        id="test_seq_daily_task_notifications",
        name="Test - thông báo task cho staff (sau 0 phút)",
        replace_existing=True,
    )
    scheduler.add_job(
        send_daily_report_request,
        trigger=DateTrigger(run_date=staff_report_time),
        id="test_daily_report_request",
        name="Test - nhắc báo cáo cuối ngày (sau 1 phút)",
        replace_existing=True,
    )

    scheduler.add_job(
        send_manager_report_for_day,
        trigger=DateTrigger(run_date=manager_report_time),
        kwargs={"manager_ids": manager_ids},
        id="test_previous_day_manager_report",
        name="Test - tổng hợp báo cáo cho manager (sau 5 phút)",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Test scheduler started. Staff report at %s, manager report at %s",
        staff_report_time.isoformat(),
        manager_report_time.isoformat(),
    )

    # # Đợi đủ thời gian để hai job chạy xong (thêm đệm 2 phút)
    # total_wait = (manager_report_time - now).total_seconds() + 120
    # await asyncio.sleep(total_wait)

    # test_scheduler.shutdown()
    # logger.info("Test scheduler stopped")


# if __name__ == "__main__":
#     asyncio.run(main())