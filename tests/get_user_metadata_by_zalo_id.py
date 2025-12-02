import requests
import json

# Zalo User ID to search
zalo_user_id = "zalo_test_001"

# API endpoint
url = f"http://localhost:8000/api/zalo-users/{zalo_user_id}/"

headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print(f"✓ User found with Zalo ID: {zalo_user_id}")
        print("\nFull Data:")
        print(json.dumps(response.json(), indent=2))
    elif response.status_code == 404:
        print(f"✗ User not found with Zalo ID: {zalo_user_id}")
    else:
        print(f"✗ Failed. Status code: {response.status_code}")
        print("Response:", response.text)
        
except requests.exceptions.RequestException as e:
    print(f"✗ Error: {e}")