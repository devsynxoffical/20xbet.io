from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import MLMLevel, UserLevel, Commission
from wallet.models import Wallet, Transaction

class MLMViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def upgrade(self, request):
        level_id = request.data.get('level_id')
        try:
            target_level = MLMLevel.objects.get(level=level_id)
        except MLMLevel.DoesNotExist:
            return Response({'error': 'Invalid level'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        wallet = user.wallet

        if wallet.balance < target_level.price:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Deduct balance
            wallet.balance -= target_level.price
            wallet.save()

            # Record Transaction
            Transaction.objects.create(
                user=user,
                amount=target_level.price,
                transaction_type='WITHDRAWAL', # Or specific type for upgrade
                status='COMPLETED',
                description=f'Upgrade to Level {target_level.level}'
            )

            # Update User Level
            UserLevel.objects.update_or_create(user=user, defaults={'current_level': target_level})

            # Distribute Commissions
            self.distribute_commissions(user, target_level.price)

        return Response({'status': 'Upgraded successfully'})

    def distribute_commissions(self, source_user, amount):
        current_upline = source_user.referrer
        for i in range(1, 6): # 5 Levels
            if not current_upline:
                break
            
            # Get commission percent for this level (simplified: assuming fixed % per level from config)
            # In real scenario, fetch from DB or config based on level 'i'
            # Example: L1=10%, L2=8%, etc.
            percent = self.get_commission_percent(i)
            commission_amount = (amount * percent) / 100

            if commission_amount > 0:
                # Add to upline wallet
                upline_wallet, _ = Wallet.objects.get_or_create(user=current_upline)
                upline_wallet.balance += commission_amount
                upline_wallet.save()

                # Record Commission
                Commission.objects.create(
                    user=current_upline,
                    source_user=source_user,
                    amount=commission_amount,
                    level=i
                )
                
                # Record Transaction for upline
                Transaction.objects.create(
                    user=current_upline,
                    amount=commission_amount,
                    transaction_type='COMMISSION',
                    status='COMPLETED',
                    description=f'Commission from {source_user.username} (Level {i})'
                )

            current_upline = current_upline.referrer

    def get_commission_percent(self, level):
        # Hardcoded for now based on example, or fetch from DB
        rates = {1: 10, 2: 8, 3: 5, 4: 3, 5: 2}
        return rates.get(level, 0)
