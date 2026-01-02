import requests
import json

BASE_URL = 'http://127.0.0.1:8000/api'

def test_registration():
    print("Testing Registration...")
    data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123',
        'phone_number': '1234567890'
    }
    try:
        response = requests.post(f'{BASE_URL}/users/register/', data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 201
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    if test_registration():
        print("Registration Test Passed")
    else:
        print("Registration Test Failed")
