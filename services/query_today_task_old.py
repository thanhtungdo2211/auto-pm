import requests
from typing import List, Dict, Optional
from datetime import datetime, date
import json

# Configuration
ZALO_WEBHOOK_BASE_URL = "http://zalooawebhook.demo.mqsolutions.vn/api"
PLANE_BASE_URL = "http://localhost:8000"
WORKSPACE_SLUG = "thang"
PLANE_API_KEY = "plane_api_d958d52c6c0845cb94b8dadd7fef425e"

def get_user_from_zalo(email: str) -> Optional[Dict]:
    """
    Fetch user details from Zalo webhook server by email
    """
    try:
        url = f"{ZALO_WEBHOOK_BASE_URL}/users/email/{email}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "success":
            return data.get("user")
        return None
    except Exception as e:
        print(f"Error fetching user from Zalo for {email}: {e}")
        return None

def get_workspace_projects() -> List[Dict]:
    """
    Fetch all projects in the workspace
    """
    try:
        url = f"{PLANE_BASE_URL}/api/v1/workspaces/{WORKSPACE_SLUG}/projects/"
        headers = {"x-api-key": PLANE_API_KEY}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except Exception as e:
        print(f"Error fetching projects: {e}")
        return []

def get_project_members(project_id: str) -> List[Dict]:
    """
    Fetch members of a specific project
    """
    try:
        url = f"{PLANE_BASE_URL}/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/members/"
        headers = {"x-api-key": PLANE_API_KEY}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching project members for {project_id}: {e}")
        return []

def get_project_issues(project_id: str, today_str: str) -> List[Dict]:
    """
    Fetch issues for a project that are in progress today (start_date <= today <= target_date)
    """
    try:
        url = f"{PLANE_BASE_URL}/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/issues/"
        headers = {"x-api-key": PLANE_API_KEY}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        all_issues = data.get("results", [])
        
        # Filter issues that are in progress today (start <= today <= target)
        today_issues = []
        for issue in all_issues:
            start_date = issue.get("start_date")
            target_date = issue.get("target_date")
            
            # Skip if either date is missing
            if not start_date or not target_date:
                continue
            
            # Check if today is between start and target (inclusive)
            if start_date <= today_str <= target_date:
                # print(f"  ✓ {issue.get('name')}")
                # print(f"    [{start_date} <= {today_str} <= {target_date}]")
                today_issues.append(issue)
        
        return today_issues
    except Exception as e:
        print(f"Error fetching issues for project {project_id}: {e}")
        return []

def build_user_task_mapping() -> Dict[str, Dict]:
    """
    Build a mapping of users to their tasks for today
    Returns: {
        user_email: {
            "user_info": {...},
            "zalo_info": {...},
            "tasks": [
                {
                    "project_name": "...",
                    "project_id": "...",
                    "issue": {...}
                }
            ]
        }
    }
    """
    today_str = date.today().isoformat()
    user_task_map = {}
    
    # Get all projects
    projects = get_workspace_projects()
    print(f"Found {len(projects)} projects in workspace '{WORKSPACE_SLUG}'")
    print(f"Checking for issues in progress on: {today_str}\n")
    
    for project in projects:
        project_id = project.get("id")
        project_name = project.get("name")
        print(f"Processing project: {project_name} ({project_id})")
        
        # Get project members
        members = get_project_members(project_id)
        member_map = {m.get("id"): m for m in members}
        # print(f"  - Found {len(members)} members")
        
        # Get today's issues for this project
        issues = get_project_issues(project_id, today_str)
        # print(f"  - Found {len(issues)} issues in progress\n")
        
        # Map issues to users
        for issue in issues:
            assignees = issue.get("assignees", [])
            
            for assignee_id in assignees:
                member_info = member_map.get(assignee_id)
                
                if not member_info:
                    print(f"    Warning: Assignee {assignee_id} not found in project members")
                    continue
                
                email = member_info.get("email")
                
                if not email:
                    print(f"    Warning: No email for member {assignee_id}")
                    continue
                
                # Initialize user entry if not exists
                if email not in user_task_map:
                    zalo_info = get_user_from_zalo(email)
                    user_task_map[email] = {
                        "user_info": member_info,
                        "zalo_info": zalo_info,
                        "tasks": []
                    }
                
                # Add task to user
                user_task_map[email]["tasks"].append({
                    "project_name": project_name,
                    "project_id": project_id,
                    "issue": {
                        "id": issue.get("id"),
                        "name": issue.get("name"),
                        "priority": issue.get("priority"),
                        "start_date": issue.get("start_date"),
                        "target_date": issue.get("target_date"),
                        "state": issue.get("state"),
                        "description_html": issue.get("description_html"),
                    }
                })
    
    return user_task_map

def format_user_tasks_for_notification(user_task_map: Dict[str, Dict]) -> List[Dict]:
    """
    Format the user task mapping for notification sending
    Returns: List of users with their tasks ready for notification
    """
    notification_data = []
    
    for email, user_data in user_task_map.items():
        user_info = user_data["user_info"]
        zalo_info = user_data["zalo_info"]
        tasks = user_data["tasks"]
        
        notification_entry = {
            "email": email,
            "display_name": user_info.get("display_name"),
            "first_name": user_info.get("first_name"),
            "last_name": user_info.get("last_name"),
            "zalo_user_id": zalo_info.get("zalo_user_id") if zalo_info else None,
            "phone": zalo_info.get("phone") if zalo_info else None,
            "task_count": len(tasks),
            "tasks": tasks
        }
        
        notification_data.append(notification_entry)
    
    return notification_data

def save_results(data: Dict, filename: str = "data/daily_tasks.json"):
    """
    Save results to JSON file
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to {filename}")

def main():
    """
    Main function to execute the daily task query
    """
    print("=" * 80)
    print(f"Daily Task Query - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Build user task mapping
    user_task_map = build_user_task_mapping()
    
    # Format for notifications
    notification_data = format_user_tasks_for_notification(user_task_map)
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total users with tasks today: {len(notification_data)}")
    
    for user in notification_data:
        print(f"\n{user['display_name']} ({user['email']}):")
        print(f"  - Zalo User ID: {user['zalo_user_id']}")
        print(f"  - Total tasks: {user['task_count']}")
        
        for task in user['tasks']:
            print(f"    • [{task['project_name']}] {task['issue']['name']}")
            print(f"      Priority: {task['issue']['priority']}, Due: {task['issue']['target_date']}")
    
    # Save results
    save_results({
        "query_date": date.today().isoformat(),
        "query_time": datetime.now().isoformat(),
        "total_users": len(notification_data),
        "users": notification_data
    })
    
    return notification_data

if __name__ == "__main__":
    main()