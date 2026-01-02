from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Wallet, Transaction

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'address', 'created_at')
    search_fields = ('user__username', 'user__email', 'address')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'status', 'created_at', 'action_buttons')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('user__username', 'user__email', 'tx_hash')
    readonly_fields = ('created_at', 'processed_at', 'processed_by')
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('user', 'transaction_type', 'amount', 'status', 'tx_hash', 'description')
        }),
        ('Proof & Admin', {
            'fields': ('deposit_proof', 'admin_notes', 'processed_by', 'processed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def action_buttons(self, obj):
        if obj.status == 'PENDING':
            return format_html(
                '<a class="button" href="/admin/wallet/transaction/{}/approve/">Approve</a> '
                '<a class="button" href="/admin/wallet/transaction/{}/reject/">Reject</a>',
                obj.pk, obj.pk
            )
        return format_html('<span style="color: green;">Processed</span>')
    action_buttons.short_description = 'Actions'
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/approve/', self.admin_site.admin_view(self.approve_transaction), name='approve-transaction'),
            path('<int:pk>/reject/', self.admin_site.admin_view(self.reject_transaction), name='reject-transaction'),
        ]
        return custom_urls + urls
    
    def approve_transaction(self, request, pk):
        from django.shortcuts import redirect
        from django.contrib import messages
        
        transaction = Transaction.objects.get(pk=pk)
        wallet = transaction.user.wallet
        
        if transaction.transaction_type == 'DEPOSIT':
            wallet.balance += transaction.amount
            wallet.save()
        elif transaction.transaction_type == 'WITHDRAWAL':
            if wallet.balance >= transaction.amount:
                wallet.balance -= transaction.amount
                wallet.save()
            else:
                messages.error(request, 'Insufficient balance for withdrawal')
                return redirect('admin:wallet_transaction_changelist')
        
        transaction.status = 'COMPLETED'
        transaction.processed_by = request.user
        transaction.processed_at = timezone.now()
        transaction.save()
        
        messages.success(request, f'Transaction {pk} approved successfully')
        return redirect('admin:wallet_transaction_changelist')
    
    def reject_transaction(self, request, pk):
        from django.shortcuts import redirect
        from django.contrib import messages
        
        transaction = Transaction.objects.get(pk=pk)
        transaction.status = 'REJECTED'
        transaction.processed_by = request.user
        transaction.processed_at = timezone.now()
        transaction.save()
        
        messages.success(request, f'Transaction {pk} rejected')
        return redirect('admin:wallet_transaction_changelist')
