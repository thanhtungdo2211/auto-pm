import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AIReportParser:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def parse_daily_report(self, report_text: str) -> Optional[Dict]:
        """
        Parse Vietnamese daily report using Gemini Flash (FREE)
        """
        prompt = f"""Parse this Vietnamese daily work report into structured JSON.

Report: "{report_text}"

Extract all tasks mentioned with:
- title: task name/description in Vietnamese
- task_id: short identifier (extract from text or generate like TASK-1, TASK-2)
- progress: 0-100% (infer from Vietnamese phrases:
  - "hoàn thành" / "xong" = 100%
  - "đang làm" / "chưa xong" = 50%
  - or extract explicit percentages)
- time_spent: in hours format like "8h" (convert Vietnamese:
  - "cả ngày" = 8h
  - "buổi sáng" = 4h
  - "buổi chiều" = 4h
  - "X tiếng" / "X giờ" = Xh)
- status: "completed" if 100%, else "in_progress"

Return ONLY valid JSON (no markdown, no explanation):
{{
  "tasks": [
    {{
      "title": "...",
      "task_id": "...",
      "progress": 100,
      "time_spent": "8h",
      "status": "completed"
    }}
  ]
}}

If no tasks found, return: {{"tasks": []}}"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Remove markdown code blocks if present
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
                text = text.strip()
            
            result = json.loads(text)
            
            # Validate structure
            if 'tasks' not in result or not isinstance(result['tasks'], list):
                logger.error(f"Invalid AI response structure: {result}")
                return None
            
            logger.info(f"AI parsed {len(result['tasks'])} tasks from report")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"AI response is not valid JSON: {response.text}")
            return None
        except Exception as e:
            logger.error(f"AI parsing error: {e}")
            return None


def create_daily_progress_payload(parsed_report: Dict, notes: str) -> Dict:
    """
    Create API payload from parsed report
    
    Args:
        parsed_report: Dict from parse_daily_report
        notes: Original report text
    
    Returns:
        Payload dict for API
    """
    tasks = parsed_report.get('tasks', [])
    
    # Calculate achievements
    achievements = [
        f"Completed {task['title']}" 
        for task in tasks 
        if task['status'] == 'completed'
    ]
    
    payload = {
        "day": parsed_report.get('report_date', datetime.now().strftime('%Y-%m-%d')),
        "daily_tasks": {
            "tasks": [
                {
                    "id": task['task_id'],
                    "title": task['title'],
                    "status": task['status'],
                    "progress": task['progress'],
                    "time_spent": task['time_spent']
                }
                for task in tasks
            ],
            "achievements": achievements,
            "blockers": []
        },
        "notes": notes
    }
    
    return payload

if __name__ == "__main__":
    
    arp = AIReportParser()

    report_text = "báo cáo công việc ngày hôm nay : Vì hôm nay tôi làm rất năng suất nên tôi đã hoàn thành task Test module nhận diện khuôn mặt với nhiệm vụ là training mô hình"
    
    json_dr = arp.parse_daily_report(report_text)
    if json_dr is None:
        print("No parsed report")
    else:
        print("Parsed report:")
        print(json.dumps(json_dr, ensure_ascii=False, indent=2))

        payload = create_daily_progress_payload(json_dr, report_text)
        print("\nPayload:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))