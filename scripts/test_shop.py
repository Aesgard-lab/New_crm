
import requests
import json
import base64

# Use the credentials we just verified
email = "demo.cliente@mygym.com"
password = "password123"

# 1. Login to get token
login_url = 'http://127.0.0.1:8000/api/auth/login/'
login_payload = {
    'email': email,
    'password': password
}
try:
    print(f"Logging in as {email}...")
    resp = requests.post(login_url, json=login_payload)
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} {resp.text}")
        exit()
    
    data = resp.json()
    token = data['token']
    print("Login successful! Token obtained.")
except Exception as e:
    print(f"Login error: {e}")
    exit()

# 2. Test Shop Endpoint
shop_url = 'http://127.0.0.1:8000/api/shop/'
headers = {
    'Authorization': f'Token {token}',
    'Content-Type': 'application/json'
}

print(f"\nRequesting Shop Data from {shop_url}...")
try:
    resp = requests.get(shop_url, headers=headers)
    print(f"Shop Status: {resp.status_code}")
    if resp.status_code == 200:
        shop_data = resp.json()
        print("Shop Data keys:", shop_data.keys())
        print(f"Products: {len(shop_data.get('products', []))}")
        print(f"Services: {len(shop_data.get('services', []))}")
        print(f"Plans: {len(shop_data.get('membership_plans', []))}")
        print("SAMPLE DATA:")
        print(json.dumps(shop_data, indent=2))
    else:
        print("Shop Error Response:")
        print(resp.text)

except Exception as e:
    print(f"Shop request error: {e}")
