import requests
import json
import os

# API endpoint
PLANE_BASE_URL = os.getenv("PLANE_API_URL", "975a90a00e3d.ngrok-free.app")
WORKSPACE_SLUG = os.getenv("WORKSPACE_SLUG", "thang")

url = f"https://{PLANE_BASE_URL}/api/workspaces/{WORKSPACE_SLUG}/add-member/"

# Member data
data = {
    "email": "tungdt.8383@gmail.com",
    "role": 15
}

# Headers with API key
headers = {
    "Content-Type": "application/json",
    "x-api-key": "plane_api_fe15a1874a304088b027ce4bbe8afc23"
}

# Make POST request
try:
    response = requests.post(url, headers=headers, json=data)
    
    # Check if request was successful
    if response.status_code in [200, 201]:
        print("Member added successfully!")
        print("Response:", response.json())
    else:
        print(f"Failed to add member. Status code: {response.status_code}")
        print("Response:", response.text)
        
except requests.exceptions.RequestException as e:
    print(f"Error making request: {e}")