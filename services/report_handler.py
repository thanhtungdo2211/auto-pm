import os
import logging
from typing import Dict, List

import httpx
from dotenv import load_dotenv
from services.report_parser import parse_daily_report, create_daily_progress_payload

logger = logging.getLogger(__name__)

load_dotenv('./.env')


PLANE_BASE_URL = os.getenv("PLANE_API_URL", "https://af3142515b93.ngrok-free.app")
WORKSPACE_SLUG = os.getenv("WORKSPACE_SLUG", "thang")
PLANE_API_KEY = os.getenv("PLANE_API_KEY", "plane_api_fe15a1874a304088b027ce4bbe8afc23")

class ReportHandler:
    def __init__(self):
        self.base_url = PLANE_BASE_URL
        self.api_key = PLANE_API_KEY
    
    async def save_daily_progress(
        self,
        project_id: str,
        issue_id: str,
        parsed_report: Dict,
        notes: str
    ) -> bool:
        """
        Save daily progress for a specific issue
        """
        try:
            payload = create_daily_progress_payload(parsed_report, notes)
            
            url = f"{self.base_url}/api/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/issues/{issue_id}/daily-progress/"
            
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key
            }
            
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(url, json=payload, headers=headers, timeout=30.0)
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ Daily progress saved for issue {issue_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to save progress. Status: {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error saving daily progress: {e}")
            return False
    
    async def process_staff_report(
        self,
        zalo_user_id: str,
        report_text: str,
        user_tasks: List[Dict],
    ) -> Dict:
        """
        Process staff's daily report and save to all their issues
        
        Args:
            zalo_user_id: User's Zalo ID
            report_text: The report message text
            user_tasks: List of tasks from query_today_tasks
            workspace_slug: Workspace slug
        
        Returns:
            Dict with processing results
        """
        try:
            # Parse the report
            parsed_report = parse_daily_report(report_text)
            if not parsed_report:
                logger.error("Failed to parse report")
                return {
                    "success": False,
                    "error": "Cannot parse report",
                    "message": "❌ Không thể đọc được báo cáo của bạn.\n\nVui lòng gửi lại theo định dạng:\nBáo cáo công việc ngày hôm nay:\nTask A: 60%, 3 tiếng. Task B: 100%, 4 tiếng."
                }
            
            if not user_tasks:
                logger.warning(f"No tasks found for user {zalo_user_id}")
                return {
                    "success": False,
                    "error": "No tasks found",
                    "message": "⚠️ Không tìm thấy task nào được gán cho bạn hôm nay."
                }
            
            # Save progress for each task/issue
            saved_count = 0
            failed_issues = []
            
            for task in user_tasks:
                project_id = task.get('project_id')
                issue_id = task.get('issue', {}).get('id')
                
                if not project_id or not issue_id:
                    logger.warning(f"Missing project_id or issue_id in task: {task}")
                    continue
                
                success = await self.save_daily_progress(
                    workspace_slug=WORKSPACE_SLUG,
                    project_id=project_id,
                    issue_id=issue_id,
                    parsed_report=parsed_report,
                    notes=report_text
                )
                
                if success:
                    saved_count += 1
                else:
                    failed_issues.append(task.get('issue', {}).get('name', 'Unknown'))
            
            # Build response message
            if saved_count > 0:
                task_summary = "\n".join([
                    f"• {task['title']}: {task['progress']}% ({task['time_spent']})"
                    for task in parsed_report['tasks']
                ])
                
                confirmation_msg = f"✅ Cảm ơn bạn đã gửi báo cáo!\n\n"
                confirmation_msg += f"Báo cáo đã được ghi nhận cho {saved_count} task:\n\n"
                confirmation_msg += task_summary + "\n\n"
                confirmation_msg += "📊 Báo cáo sẽ được tổng hợp và gửi cho quản lý vào 8h sáng mai."
                
                if failed_issues:
                    confirmation_msg += f"\n\n⚠️ Không thể lưu báo cáo cho: {', '.join(failed_issues)}"
                
                return {
                    "success": True,
                    "saved_count": saved_count,
                    "failed_count": len(failed_issues),
                    "message": confirmation_msg
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to save reports",
                    "message": "❌ Có lỗi khi lưu báo cáo. Vui lòng thử lại sau."
                }
                
        except Exception as e:
            logger.error(f"Error processing staff report: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "❌ Có lỗi xảy ra khi xử lý báo cáo. Vui lòng thử lại sau."
            }