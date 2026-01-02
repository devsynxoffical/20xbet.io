
import os
import django
import sys
from decimal import Decimal

# Setup Django environment
sys.path.append('d:/Betting Site') # Add parent of backend folder
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mlm_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from wallet.models import Wallet, Transaction
from wallet.services import CommissionService

User = get_user_model()

def run_test():
    print("--- Starting Commission Test (ORM Mode) ---")
    
    # 1. Cleanup previous test data
    User.objects.filter(email__contains='@test.local').delete()
    User.objects.filter(username__in=['salary_fund', 'reserve_fund']).delete()
    print("Cleaned up old test users.")

    # 2. Create Users
    users = []
    referrer = None
    
    usernames = ['UserTop', 'UserL2', 'UserL3', 'UserL4', 'UserL5', 'UserBetter']
    
    for name in usernames:
        user = User.objects.create_user(
            username=name,
            email=f"{name.lower()}@test.local",
            password="pass",
            is_approved=True,  # Auto approve for test
            referrer=referrer
        )
        # Create wallet
        Wallet.objects.create(user=user, balance=Decimal('100.00'))
        users.append(user)
        referrer = user
        print(f"Created {name} with referrer {referrer.username if referrer != user else 'None'}")

    user_better = users[-1] # UserBetter
    
    # 3. Simulate Bet Loss
    loss_amount = Decimal('10.00')
    print(f"\nProcessing bet loss of ${loss_amount} for {user_better.username}...")
    
    # Deduct balance
    user_better.wallet.balance -= loss_amount
    user_better.wallet.save()
    
    # Run distribution logic
    CommissionService.process_bet_loss(user_better, loss_amount)
    
    # 4. Verify Results
    print("\n--- Verification Results ---")
    
    # Check UserBetter balance
    user_better.wallet.refresh_from_db()
    print(f"UserBetter Balance: {user_better.wallet.balance} (Expected 90.00)")
    
    # Check Funds
    salary = User.objects.get(username='salary_fund').wallet
    reserve = User.objects.get(username='reserve_fund').wallet
    
    print(f"Salary Fund: ${salary.balance} (Expected 1.00)")
    print(f"Reserve Fund: ${reserve.balance} (Expected 6.50)")
    
    # Check Upline
    # UserBetter -> UserL5 -> UserL4 -> UserL3 -> UserL2 -> UserTop
    # Index:       4          3          2          1          0
    
    # Only 5 levels up. 
    # Logic: current_user = user_better (index 5)
    # Level 1 referrer: users[4] (UserL5) -> 11% ($1.10)
    # Level 2 referrer: users[3] (UserL4) -> 9% ($0.90)
    # Level 3 referrer: users[2] (UserL3) -> 2% ($0.20)
    # Level 4 referrer: users[1] (UserL2) -> 1.5% ($0.15)
    # Level 5 referrer: users[0] (UserTop) -> 1.5% ($0.15)
    
    expectations = [
        (4, '1.10'), (3, '0.90'), (2, '0.20'), (1, '0.15'), (0, '0.15')
    ]
    
    for idx, expected in expectations:
        u = users[idx]
        u.wallet.refresh_from_db()
        # Initial balance 100
        total_expected = Decimal('100.00') + Decimal(expected)
        print(f"{u.username}: ${u.wallet.balance} (Expected {total_expected})")

if __name__ == "__main__":
    run_test()
