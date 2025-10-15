# ...existing code...
import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ACCESSTOKEN = "olou5wuyUMFD-R4Ph3v_RSxwingf9GriZEQgRB4aDboedu1SbaCHPh3ukXBNRcywxlJsFTenEXpuaPqAymmHFCEgeXJv37SZvON8B80uMotag-O-t39F5SEss3xUS4a8wldkB-TzUG3Qkj5tmWTFNCMNzNBV4a9ZoudEOFGAJ6oIoy9nXWvNP8w7_HMuBcy_eAt2BeHa3YY-rvvIdd4yOwdHgqIFMJLsbD-7MhOS9N6JW9nAaZDJVxUoqLVL07CbjiFbDgbPHqUOtFnVY1XJ9A2ccHwBCGOqavcT8VGFFpJLaBucpJG12yg9lWlW21yazgZGNiDhMI_SgjjTp7PFK-dlz4V8Mbv6sFBaRUTrVWBNxFSLl75d3R_dyJkaStyWeCo-3grh2pgGzyOna6ncCQEfznQQ7KOvKl7uGgmZSsO"

def test_send_message(user_id, message):
    payload = {
        "recipient": {
            "user_id": user_id
        },
        "message": {
            "text": message
        }
    }
    headers = {
        "access_token": ACCESSTOKEN,
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://openapi.zalo.me/v3.0/oa/message/cs",
        json=payload,
        headers=headers,
        timeout=10
        )
    print(response.json())
    print(response.status_code)

if __name__ == "__main__":
    test_send_message()