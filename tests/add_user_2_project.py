import requests
import json

# API endpoint configuration
workspace_slug = "thang"
project_id = "741c0b5a-6d3c-4afb-af41-9ff320443db7"
url = f"https://975a90a00e3d.ngrok-free.app/api/workspaces/{workspace_slug}/projects/{project_id}/add-member/"

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
        print("✓ Project member added successfully!")
        print(f"Status Code: {response.status_code}")
        print("Response Data:")
        print(json.dumps(response.json(), indent=2))
    elif response.status_code == 400:
        print("✗ Bad Request - Check your data format")
        print("Response:", response.text)
    elif response.status_code == 401:
        print("✗ Unauthorized - Check your API key")
        print("Response:", response.text)
    elif response.status_code == 404:
        print("✗ Not Found - Check workspace slug and project ID")
        print("Response:", response.text)
    else:
        print(f"✗ Failed to add project member. Status code: {response.status_code}")
        print("Response:", response.text)
        
except requests.exceptions.ConnectionError:
    print("✗ Connection Error - Make sure the server is running on localhost:8000")
except requests.exceptions.Timeout:
    print("✗ Request Timeout - Server took too long to respond")
except requests.exceptions.RequestException as e:
    print(f"✗ Error making request: {e}")
except json.JSONDecodeError:
    print("✗ Could not parse JSON response")
    print("Raw response:", response.text)