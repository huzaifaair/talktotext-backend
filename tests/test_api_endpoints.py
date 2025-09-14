import requests

BASE = "http://localhost:8000/api"

def test_health():
    r = requests.get(BASE + "/health")
    print("Health:", r.json())

if __name__ == "__main__":
    test_health()
