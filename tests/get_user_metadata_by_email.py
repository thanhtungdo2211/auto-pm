import requests
import json

# Email to search
email = "testuser2@example.com"

# API endpoint
url = f"http://localhost:8000/api/users/with-zalo/?email={email}"

headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print(f"✓ User found: {email}")
        user_data = response.json()
        
        print("\n" + "="*50)
        print("USER INFORMATION")
        print("="*50)
        print(f"ID: {user_data.get('id')}")
        print(f"Username: {user_data.get('username')}")
        print(f"Email: {user_data.get('email')}")
        print(f"Name: {user_data.get('first_name')} {user_data.get('last_name')}")
        
        if user_data.get('zalo_metadata'):
            print("\n" + "="*50)
            print("ZALO METADATA")
            print("="*50)
            zalo = user_data['zalo_metadata']
            print(f"Zalo User ID: {zalo.get('zalo_user_id')}")
            print(f"Name: {zalo.get('name')}")
            print(f"Phone: {zalo.get('phone')}")
            print(f"Role: {zalo.get('role')}")
            print(f"Skills: {zalo.get('skills')}")
            print(f"Description: {zalo.get('description')}")
            print(f"CV: {zalo.get('cv')}")
            print(f"CV Data: {json.dumps(zalo.get('cv_data'), indent=2)}")
            print(f"Additional Info: {json.dumps(zalo.get('additional_info'), indent=2)}")
        else:
            print("\n✗ No Zalo metadata found for this user")
        
        print("\n" + "="*50)
        print("FULL RESPONSE")
        print("="*50)
        print(json.dumps(user_data, indent=2))
        
    elif response.status_code == 404:
        print(f"✗ User not found: {email}")
    else:
        print(f"✗ Failed. Status code: {response.status_code}")
        print("Response:", response.text)
        
except requests.exceptions.RequestException as e:
    print(f"✗ Error: {e}")