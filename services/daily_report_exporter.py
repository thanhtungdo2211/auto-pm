import re
from typing import Dict, List, Optional
from datetime import datetime

import requests

class DailyReportParser:
    """Parse natural language daily reports into structured data"""
    
    def __init__(self):
        # Patterns for Vietnamese text
        self.task_pattern = r'task\s+([A-Za-z0-9]+)'
        self.time_pattern = r'(\d+)\s*(?:tiếng|giờ|hours?)'
        self.progress_pattern = r'(\d+)%'
    
    def parse(self, message: str) -> Dict:
        """
        Parse daily report message into structured format
        
        Args:
            message: Natural language daily report in Vietnamese
            
        Returns:
            Dictionary with parsed tasks and metadata
        """
        tasks = self._extract_tasks(message)
        
        return {
            "day": datetime.now().strftime("%Y-%m-%d"),
            "daily_tasks": {
                "tasks": tasks,
                "achievements": self._extract_achievements(tasks),
                "blockers": []
            },
            "notes": message
        }
    
    def _extract_tasks(self, message: str) -> List[Dict]:
        """Extract individual tasks from message"""
        tasks = []
        
        # Find all task mentions
        task_names = re.findall(self.task_pattern, message, re.IGNORECASE)
        
        # Split message into sentences for context
        sentences = message.split(',')
        
        for i, task_name in enumerate(task_names):
            task_context = self._find_task_context(task_name, message)
            
            time_spent = self._extract_time(task_context)
            progress = self._extract_progress(task_context)
            
            task = {
                "id": f"task-{task_name.lower()}",
                "title": f"Task {task_name}",
                "status": "completed" if progress == 100 else "in_progress",
                "progress": progress,
                "time_spent": f"{time_spent}h" if time_spent else "0h"
            }
            tasks.append(task)
        
        return tasks
    
    def _find_task_context(self, task_name: str, message: str) -> str:
        """Find the sentence/context containing the task"""
        sentences = re.split(r'[,،]|\s+và\s+|\s+còn\s+', message)
        for sentence in sentences:
            if task_name.lower() in sentence.lower():
                return sentence
        return ""
    
    def _extract_time(self, text: str) -> Optional[int]:
        """Extract time spent from text"""
        match = re.search(self.time_pattern, text)
        return int(match.group(1)) if match else None
    
    def _extract_progress(self, text: str) -> int:
        """Extract progress percentage from text"""
        match = re.search(self.progress_pattern, text)
        return int(match.group(1)) if match else 0
    
    def _extract_achievements(self, tasks: List[Dict]) -> List[str]:
        """Generate achievements from completed tasks"""
        achievements = []
        for task in tasks:
            if task["status"] == "completed":
                achievements.append(f"Completed {task['title']}")
        return achievements

class DailyReportExporter:
    """Export daily reports to the API"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.parser = DailyReportParser()
    
    def export_report(
        self,
        message: str,
        workspace_slug: str,
        project_id: str,
        issue_id: str
    ) -> Dict:
        """
        Parse message and export to API
        
        Args:
            message: Natural language daily report
            workspace_slug: Workspace identifier
            project_id: Project identifier
            issue_id: Issue identifier
            
        Returns:
            API response
        """
        # Parse the message
        payload = self.parser.parse(message)
        print(payload)

        # # Build API URL
        # url = f"{self.base_url}/api/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/daily-progress/"
        
        # # Set headers
        # headers = {
        #     "Content-Type": "application/json",
        #     "x-api-key": self.api_key
        # }
        
        # # Send request
        # try:
        #     response = requests.post(url, json=payload, headers=headers)
        #     response.raise_for_status()
            
        #     return {
        #         "success": True,
        #         "status_code": response.status_code,
        #         "data": response.json()
        #     }
        # except requests.exceptions.RequestException as e:
        #     return {
        #         "success": False,
        #         "error": str(e),
        #         "status_code": getattr(e.response, 'status_code', None)
        #     }