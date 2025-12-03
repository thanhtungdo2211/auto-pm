import requests

workspace_slug = "thang"
project_id = "c70f7676-43c6-4a5f-962a-931a122409cb"
issue_id = "a03b4ceb-50b2-4bad-94a9-46e97b3f0d2c"

# Base URL
url = f"http://localhost:8000/api/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/daily-progress/"

headers = {
    "Content-Type": "application/json",
    "x-api-key": "plane_api_321f6a302c724a5c90adfc32f0da479e"
}

print("=== Test 1: Get all daily progress for an issue ===")

response = requests.get(url, headers=headers)
print(response.json())
exit()
try:
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print("✓ Success")
        data = response.json()
        print(f"Found {len(data)} progress entries")
        for entry in data:
            print(f"  - {entry['day']}: {entry.get('notes', 'No notes')[:50]}")
    else:
        print(f"✗ Failed. Status code: {response.status_code}")
        print("Response:", response.text)
except requests.exceptions.RequestException as e:
    print(f"✗ Error: {e}")

print("\n=== Test 2: Filter by specific day ===")
try:
    params = {"day": "2024-01-15"}
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        print("✓ Success")
        data = response.json()
        print(f"Found {len(data)} progress entries for 2024-01-15")
        if data:
            print(f"Details: {data[0]}")
    else:
        print(f"✗ Failed. Status code: {response.status_code}")
        print("Response:", response.text)
except requests.exceptions.RequestException as e:
    print(f"✗ Error: {e}")

print("\n=== Test 3: Filter by date range ===")
try:
    params = {
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    }
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        print("✓ Success")
        data = response.json()
        print(f"Found {len(data)} progress entries in January 2024")
    else:
        print(f"✗ Failed. Status code: {response.status_code}")
        print("Response:", response.text)
except requests.exceptions.RequestException as e:
    print(f"✗ Error: {e}")

# print("\n=== Test 4: Get specific progress entry ===")
# # First, get all entries to get a progress_id
# try:
#     response = requests.get(url, headers=headers)
#     if response.status_code == 200 and response.json():
#         progress_id = response.json()[0]['id']
#         detail_url = f"{url}{progress_id}/"
        
#         response = requests.get(detail_url, headers=headers)
#         if response.status_code == 200:
#             print("✓ Success - Retrieved specific progress entry")
#             print(f"Details: {response.json()}")
#         else:
#             print(f"✗ Failed. Status code: {response.status_code}")
#     else:
#         print("No progress entries found to test detail endpoint")
# except requests.exceptions.RequestException as e:
#     print(f"✗ Error: {e}")