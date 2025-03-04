import requests
import time

API_URL = "https://lease-discount-rate.onrender.com/calculate"  # Update if necessary
PING_INTERVAL = 40  # (40 seconds)

def ping_api():
    try:
        response = requests.get(API_URL, params={"date": "2024-01-01", "term": 12})
        if response.status_code == 200:
            print(f"API is alive: {response.json()}")
        else:
            print(f"API responded with status code: {response.status_code}")
    except Exception as e:
        print(f"Error pinging API: {e}")

if __name__ == "__main__":
    while True:
        ping_api()
        time.sleep(PING_INTERVAL)