from rest_framework import serializers
from .models import Wallet, Transaction

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = '__all__'

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ('user', 'processed_by', 'processed_at')

class DepositRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=20, decimal_places=8, min_value=0.01)
    deposit_proof = serializers.CharField(required=False, help_text='Transaction hash or proof URL')
    tx_hash = serializers.CharField(required=False, max_length=100)

class WithdrawalRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=20, decimal_places=8, min_value=0.01)
    wallet_address = serializers.CharField(max_length=42, required=False)

class SystemSettingsSerializer(serializers.Serializer):
    admin_wallet_address = serializers.CharField(required=False, allow_blank=True, source='admin_usdt_wallet')
    registration_fee = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    usdt_network = serializers.CharField(required=False, allow_blank=True)
    min_deposit = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    deposit_instructions = serializers.CharField(required=False, allow_blank=True)
