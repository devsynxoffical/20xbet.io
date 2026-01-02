from decimal import Decimal
from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from .models import Wallet, Transaction, SystemSettings
from .serializers import WalletSerializer, TransactionSerializer, DepositRequestSerializer, WithdrawalRequestSerializer, SystemSettingsSerializer
from .services import CommissionService

class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WalletSerializer

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def admin_wallet_address(self, request):
        """Get admin wallet address for deposits"""
        try:
            setting = SystemSettings.objects.get(key='admin_usdt_wallet')
            address = setting.value
        except SystemSettings.DoesNotExist:
            address = settings.ADMIN_USDT_WALLET_ADDRESS
            
        return Response({
            'wallet_address': address,
            'network': 'BEP-20 (Binance Smart Chain)',
            'currency': 'USDT'
        })
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def registration_fee_info(self, request):
        """Get registration fee information"""
        from decimal import Decimal
        from .models import SystemSettings
        
        # Get registration fee from SystemSettings or use default
        try:
            fee_setting = SystemSettings.objects.get(key='registration_fee')
            registration_fee = Decimal(fee_setting.value)
        except SystemSettings.DoesNotExist:
            # Default registration fee
            registration_fee = Decimal('10.00')
            
        # Get admin wallet from SystemSettings or use settings default
        try:
            wallet_setting = SystemSettings.objects.get(key='admin_usdt_wallet')
            admin_wallet = wallet_setting.value
        except SystemSettings.DoesNotExist:
            admin_wallet = settings.ADMIN_USDT_WALLET_ADDRESS
        
        return Response({
            'registration_fee': str(registration_fee),
            'admin_wallet_address': admin_wallet,
            'network': 'BEP-20 (Binance Smart Chain)',
            'currency': 'USDT'
        })

class TransactionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        # Admin sees all transactions, users see only their own
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Transaction.objects.all().order_by('-created_at')
        return Transaction.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def deposit_request(self, request):
        """Create a deposit request with proof"""
        serializer = DepositRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        transaction = Transaction.objects.create(
            user=request.user,
            amount=serializer.validated_data['amount'],
            transaction_type='DEPOSIT',
            status='PENDING',
            deposit_proof=serializer.validated_data.get('deposit_proof', ''),
            tx_hash=serializer.validated_data.get('tx_hash', ''),
            description=f"Deposit request for {serializer.validated_data['amount']} USDT"
        )
        
        return Response({
            'message': 'Deposit request submitted successfully. Please wait for admin approval.',
            'transaction': TransactionSerializer(transaction).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def withdrawal_request(self, request):
        """Create a withdrawal request - deducts balance immediately"""
        serializer = WithdrawalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        wallet = request.user.wallet
        amount = serializer.validated_data['amount']
        
        if wallet.balance < amount:
            return Response({
                'error': 'Insufficient balance'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Deduct balance immediately
        wallet.balance -= amount
        wallet.save()
        
        transaction = Transaction.objects.create(
            user=request.user,
            amount=amount,
            transaction_type='WITHDRAWAL',
            status='PENDING',
            description=f"Withdrawal request for {amount} USDT to {serializer.validated_data.get('wallet_address', 'N/A')}"
        )
        
        return Response({
            'message': 'Withdrawal request submitted successfully. Balance deducted.',
            'transaction': TransactionSerializer(transaction).data,
            'new_balance': wallet.balance
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def process_bet(self, request):
        """Process a bet result (Win/Loss)"""
        amount = request.data.get('amount')
        is_win = request.data.get('is_win', False)
        win_amount = request.data.get('win_amount', 0)
        
        if not amount:
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
            
        wallet = request.user.wallet
        if wallet.balance < Decimal(str(amount)):
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
            
        # 1. Deduct Bet Amount
        wallet.balance -= Decimal(str(amount))
        wallet.save()
        
        if not is_win:
            # LOSS: Distribute commissions
            Transaction.objects.create(
                user=request.user,
                amount=amount,
                transaction_type='BET_LOSS',
                status='COMPLETED',
                description=f"Bet Loss: {amount} USDT"
            )
            
            CommissionService.process_bet_loss(request.user, amount)
            
            return Response({
                'message': 'Bet processed (Loss)',
                'new_balance': wallet.balance,
                'result': 'LOSS'
            })
        else:
            # WIN: Credit win amount
            wallet.balance += Decimal(str(win_amount))
            wallet.save()
            
            Transaction.objects.create(
                user=request.user,
                amount=win_amount,
                transaction_type='BET_WIN',
                status='COMPLETED',
                description=f"Bet Win: {win_amount} USDT"
            )
            
            return Response({
                'message': 'Bet processed (Win)',
                'new_balance': wallet.balance,
                'result': 'WIN'
            })
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve_deposit(self, request, pk=None):
        """Admin approves deposit and credits wallet"""
        transaction = self.get_object()
        
        if transaction.transaction_type != 'DEPOSIT':
            return Response({'error': 'Not a deposit'}, status=status.HTTP_400_BAD_REQUEST)
        
        if transaction.status != 'PENDING':
            return Response({'error': 'Already processed'}, status=status.HTTP_400_BAD_REQUEST)
        
        transaction.status = 'COMPLETED'
        transaction.save()
        
        wallet, _ = Wallet.objects.get_or_create(user=transaction.user)
        wallet.balance += transaction.amount
        wallet.save()
        
        return Response({'message': 'Deposit approved', 'new_balance': wallet.balance})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject_deposit(self, request, pk=None):
        """Admin rejects deposit"""
        transaction = self.get_object()
        
        if transaction.transaction_type != 'DEPOSIT':
            return Response({'error': 'Not a deposit'}, status=status.HTTP_400_BAD_REQUEST)
        
        if transaction.status != 'PENDING':
            return Response({'error': 'Already processed'}, status=status.HTTP_400_BAD_REQUEST)
        
        transaction.status = 'REJECTED'
        transaction.save()
        
        return Response({'message': 'Deposit rejected'})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve_withdrawal(self, request, pk=None):
        """Admin approves withdrawal - balance already deducted"""
        transaction = self.get_object()
        
        if transaction.transaction_type != 'WITHDRAWAL':
            return Response({'error': 'Not a withdrawal'}, status=status.HTTP_400_BAD_REQUEST)
        
        if transaction.status != 'PENDING':
            return Response({'error': 'Already processed'}, status=status.HTTP_400_BAD_REQUEST)
        
        transaction.status = 'COMPLETED'
        transaction.save()
        
        return Response({'message': 'Withdrawal approved'})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject_withdrawal(self, request, pk=None):
        """Admin rejects withdrawal and refunds balance"""
        transaction = self.get_object()
        
        if transaction.transaction_type != 'WITHDRAWAL':
            return Response({'error': 'Not a withdrawal'}, status=status.HTTP_400_BAD_REQUEST)
        
        if transaction.status != 'PENDING':
            return Response({'error': 'Already processed'}, status=status.HTTP_400_BAD_REQUEST)
        
        transaction.status = 'REJECTED'
        transaction.save()
        
        # Refund the amount back to user's wallet
        wallet = Wallet.objects.get(user=transaction.user)
        wallet.balance += transaction.amount
        wallet.save()
        
        return Response({
            'message': 'Withdrawal rejected and refunded',
            'new_balance': wallet.balance
        }, status=status.HTTP_200_OK)

class SystemSettingsView(views.APIView):
    """Get and update system settings"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get current system settings"""
        settings_keys = [
            'admin_usdt_wallet', 
            'usdt_network', 
            'min_deposit', 
            'deposit_instructions',
            'registration_fee'
        ]
        settings_data = {}
        
        for key in settings_keys:
            try:
                setting = SystemSettings.objects.get(key=key)
                # Map admin_usdt_wallet to admin_wallet_address for frontend consistency
                if key == 'admin_usdt_wallet':
                     settings_data['admin_wallet_address'] = setting.value
                else:
                     settings_data[key] = setting.value
            except SystemSettings.DoesNotExist:
                # Default values
                defaults = {
                    'admin_usdt_wallet': 'TXYZabc123...',
                    'usdt_network': 'BEP-20 (Binance Smart Chain)',
                    'min_deposit': '10.00',
                    'registration_fee': '10.00',
                    'deposit_instructions': 'Please send USDT to the address above and submit your transaction hash.'
                }
                
                val = defaults.get(key, '')
                if key == 'admin_usdt_wallet':
                    settings_data['admin_wallet_address'] = val
                else:
                    settings_data[key] = val
        
        return Response(settings_data, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Update system settings (admin only)"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = SystemSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        updated_settings = []
        updated_settings = []
        for key, value in serializer.validated_data.items():
            db_key = key
            if key == 'admin_wallet_address':
                db_key = 'admin_usdt_wallet'
                
            if value is not None:
                setting, created = SystemSettings.objects.update_or_create(
                    key=db_key,
                    defaults={
                        'value': str(value),
                        'updated_by': request.user
                    }
                )
                updated_settings.append(key)
        
        return Response({
            'message': 'Settings updated successfully',
            'updated': updated_settings
        }, status=status.HTTP_200_OK)
