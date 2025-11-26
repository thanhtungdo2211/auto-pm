import asyncio
import httpx
from typing import List, Dict, Optional
from datetime import datetime, date
import json

# Configuration
ZALO_WEBHOOK_BASE_URL = "http://localhost:5544/api"
PLANE_BASE_URL = "https://fd2232d3f667.ngrok-free.app"
WORKSPACE_SLUG = "thang"
PLANE_API_KEY = "plane_api_d958d52c6c0845cb94b8dadd7fef425e"

async def get_user_from_zalo(email: str) -> Optional[Dict]:
    """
    Fetch user details from Zalo webhook server by email
    """
    try:
        url = f"{ZALO_WEBHOOK_BASE_URL}/users/email/{email}"
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success":
                return data.get("user")
            return None
    except Exception as e:
        print(f"Error fetching user from Zalo for {email}: {e}")
        return None

async def get_workspace_projects() -> List[Dict]:
    """
    Fetch all projects in the workspace
    """
    try:
        url = f"{PLANE_BASE_URL}/api/v1/workspaces/{WORKSPACE_SLUG}/projects/"
        headers = {
            "x-api-key": PLANE_API_KEY,
            "ngrok-skip-browser-warning": "true"  # Add this for ngrok
        }
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            print(f"Projects response status: {response.status_code}")
            print(f"Projects response: {response.text[:200]}")  # Debug
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
    except Exception as e:
        print(f"Error fetching projects: {e}")
        import traceback
        traceback.print_exc()
        return []

async def get_project_members(project_id: str) -> List[Dict]:
    """
    Fetch members of a specific project
    """
    try:
        url = f"{PLANE_BASE_URL}/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/members/"
        headers = {
            "x-api-key": PLANE_API_KEY,
            "ngrok-skip-browser-warning": "true"
        }
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error fetching project members for {project_id}: {e}")
        return []

async def get_project_issues(project_id: str, today_str: str) -> List[Dict]:
    """
    Fetch issues for a project that are in progress today
    """
    try:
        url = f"{PLANE_BASE_URL}/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/issues/"
        headers = {
            "x-api-key": PLANE_API_KEY,
            "ngrok-skip-browser-warning": "true"
        }
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        
        all_issues = data.get("results", [])
        
        # Filter issues that are in progress today
        today_issues = []
        for issue in all_issues:
            start_date = issue.get("start_date")
            target_date = issue.get("target_date")
            
            if not start_date or not target_date:
                continue
            
            if start_date <= today_str <= target_date:
                today_issues.append(issue)
        
        return today_issues
    except Exception as e:
        print(f"Error fetching issues for project {project_id}: {e}")
        return []

async def build_user_task_mapping() -> Dict[str, Dict]:
    """Build a mapping of users to their tasks for today"""
    today_str = date.today().isoformat()
    user_task_map = {}
    
    # Get all projects
    projects = await get_workspace_projects()
    print(f"Found {len(projects)} projects in workspace '{WORKSPACE_SLUG}'")
    print(f"Checking for issues in progress on: {today_str}\n")
    
    for project in projects:
        project_id = project.get("id")
        project_name = project.get("name")
        print(f"Processing project: {project_name} ({project_id})")
        
        # Get project members and issues concurrently
        members, issues = await asyncio.gather(
            get_project_members(project_id),
            get_project_issues(project_id, today_str)
        )
        
        member_map = {m.get("id"): m for m in members}
        
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
                    zalo_info = await get_user_from_zalo(email)
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
    """Format the user task mapping for notification sending"""
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

async def main():
    """Main function to execute the daily task query"""
    # Build user task mapping
    user_task_map = await build_user_task_mapping()
    
    # Format for notifications
    notification_data = format_user_tasks_for_notification(user_task_map)
    
    return notification_data

# if __name__ == "__main__":
#     result = asyncio.run(main())
#     print(json.dumps(result, indent=2))