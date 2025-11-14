
import requests
import json

# API endpoint
url = "http://localhost:8000/api/users/"

# User data
data = {
    "email": "newuser2@example.com",
    "username": "newuser2",
    "first_name": "John",
    "last_name": "Doe",
    "password": "SecurePassword123"
}

# Headers
headers = {
    "Content-Type": "application/json"
}

# Make POST request
try:
    response = requests.post(url, headers=headers, json=data)
    
    # Check if request was successful
    if response.status_code in [200, 201]:
        print("User created successfully!")
        print("Response:", response.json())
    else:
        print(f"Failed to create user. Status code: {response.status_code}")
        print("Response:", response.text)
        
except requests.exceptions.RequestException as e:
    print(f"Error making request: {e}")