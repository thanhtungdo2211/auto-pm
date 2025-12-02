import requests

import sys
sys.path.insert(1, ".")

from services.daily_report_exporter import DailyReportExporter

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "plane_api_321f6a302c724a5c90adfc32f0da479e"
workspace_slug = "thang"
project_id = "c70f7676-43c6-4a5f-962a-931a122409cb"
issue_id = "a03b4ceb-50b2-4bad-94a9-46e97b3f0d2c"

# Initialize exporter
exporter = DailyReportExporter(BASE_URL, API_KEY)

# Test message
message = "Trong ngày hôm nay tôi đã làm 2 task A và B, với task A tôi dành thời gian 3 tiếng và hoàn thiện được 60%, còn với task B tôi đã hoàn thiện được 100% trong thời gian 4 tiếng"

# Export report
result = exporter.export_report(
    message=message,
    workspace_slug=workspace_slug,
    project_id=project_id,
    issue_id=issue_id
)

# Display result
if result["success"]:
    print("✓ Daily report exported successfully")
    print(f"Status: {result['status_code']}")
    print(f"Response: {result['data']}")
else:
    print("✗ Failed to export daily report")
    print(f"Error: {result['error']}")
    if result.get('status_code'):
        print(f"Status code: {result['status_code']}")