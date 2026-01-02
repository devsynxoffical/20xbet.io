from decimal import Decimal
from django.db import transaction
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Wallet, Transaction

User = get_user_model()

class CommissionService:
    @staticmethod
    def get_or_create_system_wallet(username, email):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_active': False,  # System user cannot login
                'is_staff': False
            }
        )
        wallet, _ = Wallet.objects.get_or_create(user=user)
        return wallet

    @staticmethod
    def process_bet_loss(user, amount):
        """
        Distribute commission from a lost bet amount ($10 example):
        - Level 1: 11% ($1.10)
        - Level 2: 9% ($0.90)
        - Level 3: 2% ($0.20)
        - Level 4: 1.5% ($0.15)
        - Level 5: 1.5% ($0.15)
        - Salary Fund: 10% ($1.00)
        - Reserve Fund: 65% ($6.50)
        Total: 100%
        """
        amount = Decimal(str(amount))
        
        # 1. Distribute to Salary Fund (10%)
        salary_wallet = CommissionService.get_or_create_system_wallet('salary_fund', 'salary@system.local')
        salary_amount = amount * Decimal('0.10')
        salary_wallet.balance = Decimal(str(salary_wallet.balance)) + salary_amount
        salary_wallet.save()
        
        Transaction.objects.create(
            user=salary_wallet.user,
            amount=salary_amount,
            transaction_type='COMMISSION',
            status='COMPLETED',
            description=f"Salary Fund commission from user {user.username}'s loss"
        )
        
        # 2. Distribute to Reserve Fund (65%)
        reserve_wallet = CommissionService.get_or_create_system_wallet('reserve_fund', 'reserve@system.local')
        reserve_amount = amount * Decimal('0.65')
        reserve_wallet.balance = Decimal(str(reserve_wallet.balance)) + reserve_amount
        reserve_wallet.save()
        
        Transaction.objects.create(
            user=reserve_wallet.user,
            amount=reserve_amount,
            transaction_type='COMMISSION',
            status='COMPLETED',
            description=f"Reserve Fund commission from user {user.username}'s loss"
        )
        
        # 3. Distribute to Referral Levels (25% total)
        current_user = user
        percentages = [Decimal('0.11'), Decimal('0.09'), Decimal('0.02'), Decimal('0.015'), Decimal('0.015')]
        
        for level, percentage in enumerate(percentages, 1):
            if not current_user.referrer:
                # If no referrer, add to reserve fund
                overflow_amount = amount * percentage
                reserve_wallet.balance = Decimal(str(reserve_wallet.balance)) + overflow_amount
                reserve_wallet.save()
                break
                
            referrer = current_user.referrer
            commission_amount = amount * percentage
            
            # Credit referrer wallet
            referrer_wallet, _ = Wallet.objects.get_or_create(user=referrer)
            referrer_wallet.balance = Decimal(str(referrer_wallet.balance)) + commission_amount
            referrer_wallet.save()
            
            Transaction.objects.create(
                user=referrer,
                amount=commission_amount,
                transaction_type='COMMISSION',
                status='COMPLETED',
                description=f"Level {level} commission from {user.username}'s loss"
            )
            
            current_user = referrer

        return True
