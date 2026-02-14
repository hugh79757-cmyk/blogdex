import requests
from config import API_URL, API_KEY

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def get(path, params=None):
    r = requests.get(f"{API_URL}{path}", headers=HEADERS, params=params)
    return r.json()

def post(path, data):
    r = requests.post(f"{API_URL}{path}", headers=HEADERS, json=data)
    return r.json()
