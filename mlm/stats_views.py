from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import MLMLevel, UserLevel, Commission
from wallet.models import Wallet, Transaction
from django.db.models import Sum

class StatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        user = request.user
        wallet, _ = Wallet.objects.get_or_create(user=user)
        
        # Calculate stats
        total_earnings = Commission.objects.filter(user=user).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_deposit = Transaction.objects.filter(
            user=user, 
            transaction_type='DEPOSIT', 
            status='COMPLETED'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_withdrawal = Transaction.objects.filter(
            user=user, 
            transaction_type='WITHDRAWAL', 
            status='COMPLETED'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_investment = UserLevel.objects.filter(user=user).aggregate(Sum('current_level__price'))['current_level__price__sum'] or 0
        
        # Network stats (simplified for now, ideally recursive or pre-calculated)
        direct_referrals = user.referrals.count()
        # Indirect would need recursive query or MPTT
        
        return Response({
            'balance': wallet.balance,
            'totalEarnings': total_earnings,
            'totalDeposit': total_deposit,
            'totalWithdrawal': total_withdrawal,
            'totalInvestment': total_investment,
            'directUsers': direct_referrals,
            'indirectUsers': 0, # Placeholder for heavy query
            'totalCommission': total_earnings
        })

    @action(detail=False, methods=['get'])
    def tree(self, request):
        # Build hierarchy for the referral tree component
        user = request.user
        
        def build_tree(current_user, depth=1):
            if depth > 3: # Limit depth for performance
                return []
            
            children = []
            for ref in current_user.referrals.all():
                children.append({
                    'id': ref.id,
                    'username': ref.username,
                    'level': ref.user_level.current_level.level if hasattr(ref, 'user_level') else 0,
                    'investment': 0, # calculate if needed
                    'active': ref.is_active,
                    'children': build_tree(ref, depth + 1)
                })
            return children

        tree_data = {
            'id': user.id,
            'username': 'You',
            'level': user.user_level.current_level.level if hasattr(user, 'user_level') else 0,
            'investment': 0,
            'active': True,
            'children': build_tree(user)
        }
        
        return Response(tree_data)
