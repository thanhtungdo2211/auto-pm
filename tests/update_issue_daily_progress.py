import requests

workspace_slug = "thang"
project_id = "c70f7676-43c6-4a5f-962a-931a122409cb"
issue_id = "a03b4ceb-50b2-4bad-94a9-46e97b3f0d2c"
progress_id = "1ce1ab8c-3b18-4a4f-a345-751edab5a975"  # Replace with actual progress ID

# URL for updating a specific progress entry
url = f"http://localhost:8000/api/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/daily-progress/{progress_id}/"

# Data to update (you can update any combination of fields)
payload = {
    "daily_tasks": {
        "tasks": [
            {
                "id": "task-1",
                "title": "Implement user authentication - UPDATED",
                "status": "completed",
                "progress": 100,
                "time_spent": "5h"
            },
            {
                "id": "task-2",
                "title": "Write unit tests",
                "status": "completed",
                "progress": 100,
                "time_spent": "2h"
            },
            {
                "id": "task-3",
                "title": "Code review",
                "status": "in_progress",
                "progress": 50,
                "time_spent": "1h"
            }
        ],
        "blockers": [],
        "achievements": ["Completed authentication", "All tests passing"]
    },
    "notes": "Updated: All authentication work completed. Moving to code review."
}

headers = {
    "Content-Type": "application/json",
    "x-api-key": "plane_api_321f6a302c724a5c90adfc32f0da479e"
}

try:
    response = requests.patch(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        print("✓ Daily progress updated successfully")
        print("\nUpdated data:")
        import json
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"✗ Failed. Status code: {response.status_code}")
        print("Response:", response.text)
        
except requests.exceptions.RequestException as e:
    print(f"✗ Error: {e}")