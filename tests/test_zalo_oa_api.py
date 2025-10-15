# ...existing code...
import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ACCESSTOKEN = "ZA1YPRjUFrIBfMjhkLmvMeYcQMYyHqavqzntN9KgGMZRj5qCapXqUy6W90-Q87bP-Tah1fboUNljY4SCt2LXEhkCS0tH3Y5DvF9yV9q4IZd4Y1XC_N0p3uhQ3ZlSGI1UXTin5U0iPdsnbaeqWszwRC7HA1ZrMmvcaiOG9iHC91Rqrsqdgc9DKCAQV2M16qftkRDz0FCnIckrZLSSmYn_AhdNQ1wFBZvtnOaA0lSCBMcNytmfx6jURu3LOo7MVJ1hfUSu8fT75MluooS2k78FRzU490w6CtP_j8vuI_4NSnk_XtvgpXf8NVcTOIY-Fs5uqBbo5Q8FINpNkbLBi0HUUUNvNnAgHtH2myDN3uWqQYNdf45ca1zj6UAfUMsdF6rP_i5d0OSuGMV0b15LjmjC1TczIagK8nu3SMK1psG7kK4rKG"

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