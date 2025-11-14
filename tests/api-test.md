curl -X POST http://localhost:8000/api/workspaces/workspace-mq/members/ \
  -H "Content-Type: application/json" \
  -H "x-api-key: plane_api_ee8695a6d89a47638cc8850216e94e2e" \
  -d '{
    "email": "newuser@example.com",
    "role": 20
  }'


curl -X POST http://localhost:8000/api/workspaces/workspace-mq/members/ \
  -H "Content-Type: application/json" \
  -H "x-api-key: plane_api_ee8695a6d89a47638cc8850216e94e2e" \
  -d '{
    "email": "tung.0982548086@gmail.com",
    "role": 20
  }'


curl -X POST http://localhost:8000/api/workspaces/workspace-mq/projects/3e461a14-adb1-4211-8c57-61d455ca53c3/members/ \
  -H "Content-Type: application/json" \
  -H "x-api-key: plane_api_ee8695a6d89a47638cc8850216e94e2e" \
  -d '{
    "email": "newuser2@example.com",
    "role": 20
  }'

curl -X POST http://localhost:8000/api/auth/sign-in/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser2@example.com",
    "password": "SecurePassword123"
  }'

curl -X POST http://localhost:8000/api/workspaces/workspace-mq/projects/3e461a14-adb1-4211-8c57-61d455ca53c3/add-member/ \
  -H "Content-Type: application/json" \
  -H "x-api-key: plane_api_ee8695a6d89a47638cc8850216e94e2e" \
  -d '{
    "email": "newuser2@example.com",
    "role": 15
  }'

# Remove member khỏi workspace
curl -X DELETE http://localhost:8000/api/workspaces/workspace-mq/remove-member/83d66dd9-9775-4178-ac4b-b7cdd9c7593d/ \
  -H "x-api-key: plane_api_ee8695a6d89a47638cc8850216e94e2e"

# Remove member khỏi project
curl -X DELETE http://localhost:8000/api/workspaces/workspace-mq/projects/3e461a14-adb1-4211-8c57-61d455ca53c3/remove-member/83d66dd9-9775-4178-ac4b-b7cdd9c7593d/ \
  -H "x-api-key: plane_api_ee8695a6d89a47638cc8850216e94e2e"