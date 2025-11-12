# import requests

# url = "https://api.plane.so/api/v1/workspaces/workspacetdt/projects/"

# payload = {
#     "name": "Auto PM",
#     "identifier": "Auto PM",
#     "description": "Project for Auto PM"
# }
# headers = {
#     "x-api-key": "plane_api_b9d38852ead84787b8d1562cec8a981f",
#     "Content-Type": "application/json"
# }

# response = requests.post(url, json=payload, headers=headers)

# print(response.json())

import requests

url = "https://api.plane.so/api/v1/workspaces/workspacetdt/projects/AUTO/members/"

headers = {"x-api-key": "plane_api_b9d38852ead84787b8d1562cec8a981f"}

response = requests.get(url, headers=headers)
# 01a7d181-3634-43b9-903f-a02abd7214b4
print(response.json())