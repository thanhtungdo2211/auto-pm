import requests

workspace_slug = "thang"
project_id = "c70f7676-43c6-4a5f-962a-931a122409cb"
issue_id = "a03b4ceb-50b2-4bad-94a9-46e97b3f0d2c"  # Replace with actual issue ID

url = f"http://localhost:8000/api/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/daily-progress/"

payload = {
    "day": "2024-01-15",
    "daily_tasks": {
        # "tasks": [
        #     {
        #         "id": "task-1",
        #         "title": "Implement user authentication",
        #         "status": "in_progress",
        #         "progress": 60,
        #         "time_spent": "3h"
        #     },
        #     {
        #         "id": "task-2",
        #         "title": "Write unit tests",
        #         "status": "completed",
        #         "progress": 100,
        #         "time_spent": "2h"
        #     }
        # ],
        # "blockers": ["Waiting for API documentation"],
        # "achievements": ["Completed login flow"]
        "tung": "thang beo"
    },
    "notes": "Good progress today. Need to focus on testing tomorrow."
}

headers = {
    "Content-Type": "application/json",
    "x-api-key": "plane_api_321f6a302c724a5c90adfc32f0da479e"  # Replace with your actual API key
}

# headers = {
#     "Content-Type": "application/json"
# }

# headers = {"x-api-key": "plane_api_321f6a302c724a5c90adfc32f0da479e"}

# headers = {"x-api-key": "plane_api_321f6a302c724a5c90adfc32f0da479e"}

try:
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code in [200, 201]:
        print("✓ Daily progress created successfully")
        print(response.json())
    else:
        print(f"✗ Failed. Status code: {response.status_code}")
        print("Response:", response.text)
        
except requests.exceptions.RequestException as e:
    print(f"✗ Error: {e}")