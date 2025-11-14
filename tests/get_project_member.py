import requests

url = "http://localhost/api/v1/workspaces/workspace-mq/projects/3e461a14-adb1-4211-8c57-61d455ca53c3/members/"

headers = {"x-api-key": "plane_api_ee8695a6d89a47638cc8850216e94e2e"}

response = requests.get(url, headers=headers)

print(response.json())