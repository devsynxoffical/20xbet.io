from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Transaction
from .serializers import TransactionSerializer

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

class AdminTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.all().order_by('-created_at')
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    filterset_fields = ['status', 'transaction_type']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        transaction = self.get_object()
        
        if transaction.status != 'PENDING':
            return Response({'error': 'Transaction already processed'}, status=status.HTTP_400_BAD_REQUEST)
        
        wallet = transaction.user.wallet
        
        if transaction.transaction_type == 'DEPOSIT':
            wallet.balance += transaction.amount
            wallet.save()
            transaction.status = 'COMPLETED'
        elif transaction.transaction_type == 'WITHDRAWAL':
            if wallet.balance >= transaction.amount:
                wallet.balance -= transaction.amount
                wallet.save()
                transaction.status = 'COMPLETED'
            else:
                return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
        else:
             return Response({'error': 'Invalid transaction type for approval'}, status=status.HTTP_400_BAD_REQUEST)
             
        transaction.processed_by = request.user
        transaction.processed_at = timezone.now()
        transaction.save()
        
        return Response({'message': 'Transaction approved successfully'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        transaction = self.get_object()
        
        if transaction.status != 'PENDING':
            return Response({'error': 'Transaction already processed'}, status=status.HTTP_400_BAD_REQUEST)
            
        transaction.status = 'REJECTED'
        transaction.processed_by = request.user
        transaction.processed_at = timezone.now()
        transaction.save()
        
        return Response({'message': 'Transaction rejected'})
