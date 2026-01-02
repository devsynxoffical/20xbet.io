
# 2025-05-18 Full verification script
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def create_user(username, email, password, referrer_code=None):
    data = {
        "username": username,
        "email": email,
        "password": password,
        "phone_number": f"1234{str(hash(username))[-6:]}"
    }
    if referrer_code:
        data["referrer_code"] = referrer_code
        
    try:
        # Try login first to prevent duplicate errors
        login_res = requests.post(f"{BASE_URL}/users/login/", json={"email": email, "password": password})
        if login_res.status_code == 200:
            print(f"User {username} already exists, logging in...")
            return login_res.json()["access"], login_res.json()["user"]["referral_code"]
            
        print(f"Creating user {username}...")
        res = requests.post(f"{BASE_URL}/users/register/", json=data)
        if res.status_code == 201:
            # Login to get token
            login_res = requests.post(f"{BASE_URL}/users/login/", json={"email": email, "password": password})
            return login_res.json()["access"], login_res.json()["user"]["referral_code"]
        else:
            print(f"Failed to create user {username}: {res.text}")
            return None, None
    except Exception as e:
        print(f"Error creating user {username}: {e}")
        return None, None

def fund_wallet(token, amount=100):
    # This is a bit tricky since we don't have a direct "add money" endpoint without admin
    # But for now we can assume the user has money or we manually inject it via deposit loop
    # For this test, let's assume valid balance or use the "deposit request" + "admin approve" loop
    pass 

def test_commission():
    print("--- Starting Commission Test ---")
    
    # 1. Create Chain: UserA -> UserB -> UserC -> UserD -> UserE -> UserF
    token_a, ref_a = create_user("UserA", "usera@test.com", "Pass123!@#")
    token_b, ref_b = create_user("UserB", "userb@test.com", "Pass123!@#", ref_a)
    token_c, ref_c = create_user("UserC", "userc@test.com", "Pass123!@#", ref_b)
    token_d, ref_d = create_user("UserD", "userd@test.com", "Pass123!@#", ref_c)
    token_e, ref_e = create_user("UserE", "usere@test.com", "Pass123!@#", ref_d)
    token_f, ref_f = create_user("UserF", "userf@test.com", "Pass123!@#", ref_e)
    
    # 2. Fund UserF
    # For speed, we will manually update DB if possible, or use deposit request
    print("Funding UserF...")
    admin_token, _ = create_user("admin", "admin@20xbet.io", "admin") # Assuming admin exists
    
    # Create deposit
    headers_f = {"Authorization": f"Bearer {token_f}"}
    res = requests.post(f"{BASE_URL}/wallet/transactions/deposit_request/", json={"amount": 100, "tx_hash": "test_fund"}, headers=headers_f)
    if res.status_code == 201:
        tx_id = res.json()["transaction"]["id"]
        # Approve (need admin token)
        # Verify admin manually
        print(f"Deposit request {tx_id} created. Please ensure it is approved to continue test.")
        
    # 3. UserF places a losing bet of $10
    print("\nSimulating $10 Bet LOSS for UserF...")
    res = requests.post(f"{BASE_URL}/wallet/transactions/process_bet/", 
                        json={"amount": 10.00, "is_win": False}, 
                        headers=headers_f)
    
    print(f"Bet Result: {res.status_code}")
    print(res.json())
    
    if res.status_code == 200:
        print("\n--- Verification Required ---")
        print("Check database/admin panel transactions to see:")
        print("1. UserF balance -10")
        print("2. UserE wallet +$1.10")
        print("3. UserD wallet +$0.90")
        print("4. UserC wallet +$0.20")
        print("5. UserB wallet +$0.15")
        print("6. UserA wallet +$0.15")
        print("7. Salary Fund wallet +$1.00")
        print("8. Reserve Fund wallet +$6.50")

if __name__ == "__main__":
    test_commission()
