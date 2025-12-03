import re
from typing import Dict, List, Optional
from datetime import datetime

def parse_daily_report(report_text: str) -> Optional[Dict]:
    """
    Parse Vietnamese daily report text into structured format
    
    Example input:
    "Trong ngày hôm nay tôi đã làm 2 task A và B, với task A tôi dành thời gian 
     3 tiếng và hoàn thiện được 60%, còn với task B tôi đã hoàn thiện được 100% 
     trong thời gian 4 tiếng"
    
    Returns:
        Dict with parsed tasks or None if parsing fails
    """
    try:
        tasks = []
        
        # Pattern to find task mentions with context
        task_pattern = r'task\s+([A-Za-z0-9]+)'
        time_pattern = r'(\d+)\s*(?:tiếng|giờ|hours?)'
        progress_pattern = r'(\d+)%'
        
        # Find all task names
        task_matches = list(re.finditer(task_pattern, report_text, re.IGNORECASE))
        
        if not task_matches:
            return None
        
        # Split text into segments for each task
        for i, match in enumerate(task_matches):
            task_name = match.group(1)
            
            # Get text segment for this task (until next task or end)
            start_pos = match.start()
            end_pos = task_matches[i + 1].start() if i + 1 < len(task_matches) else len(report_text)
            task_segment = report_text[start_pos:end_pos]
            
            # Extract time and progress from segment
            time_match = re.search(time_pattern, task_segment)
            progress_match = re.search(progress_pattern, task_segment)
            
            time_spent = int(time_match.group(1)) if time_match else 0
            progress = int(progress_match.group(1)) if progress_match else 0
            
            tasks.append({
                'title': f'Task {task_name}',
                'task_id': task_name.upper(),
                'progress': progress,
                'time_spent': f'{time_spent}h',
                'status': 'completed' if progress == 100 else 'in_progress'
            })
        
        if not tasks:
            return None
        
        return {
            'tasks': tasks,
            'total_time': sum(int(t['time_spent'].rstrip('h')) for t in tasks),
            'report_date': datetime.now().strftime('%Y-%m-%d')
        }
        
    except Exception as e:
        print(f"Error parsing report: {e}")
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