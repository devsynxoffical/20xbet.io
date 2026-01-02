from rest_framework import serializers
from django.contrib.auth import get_user_model
from .utils import generate_verification_token, generate_otp_secret

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    referrer_code = serializers.CharField(write_only=True, required=False)
    wallet_address = serializers.CharField(max_length=42, required=False, allow_blank=True)
    registration_fee_tx_hash = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'phone_number', 'password', 'referral_code', 'referrer_code', 'wallet_address', 'registration_fee_tx_hash')
        read_only_fields = ('referral_code',)
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True},
            'phone_number': {'required': False, 'allow_blank': True},
            'username': {'required': True},
        }

    def validate_wallet_address(self, value):
        if value:
            # Check if address already exists
            if User.objects.filter(wallet_address__iexact=value).exists():
                raise serializers.ValidationError('Wallet address already registered')
        return value

    def validate_email(self, value):
        if value:
            if User.objects.filter(email__iexact=value).exists():
                raise serializers.ValidationError('Email address already registered')
        return value

    def validate(self, data):
        wallet_address = data.get('wallet_address')
        email = data.get('email')
        password = data.get('password')
        
        # Wallet Logic
        if wallet_address:
            # Auto-generate email if missing
            if not email:
                data['email'] = f"{wallet_address.lower()}@wallet.local"
        # Traditional Logic
        else:
            if not password:
                raise serializers.ValidationError({'password': 'Password is required for email-based registration'})
            if not email:
                raise serializers.ValidationError({'email': 'Email is required'})
            
        return data

    def create(self, validated_data):
        referrer_code = validated_data.pop('referrer_code', None)
        wallet_address = validated_data.pop('wallet_address', None)
        password = validated_data.pop('password', None)
        email = validated_data.get('email')
        
        referrer = None
        if referrer_code:
            try:
                referrer = User.objects.get(referral_code=referrer_code)
            except User.DoesNotExist:
                pass # Ignore invalid referral code
        
        # Generate Referral Code
        import random
        import string
        def generate_ref_code():
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
        referral_code = generate_ref_code()
        while User.objects.filter(referral_code=referral_code).exists():
            referral_code = generate_ref_code()
        
        # Create User
        if wallet_address:
            # Wallet User
            user = User(
                username=validated_data['username'],
                email=email,
                phone_number=validated_data.get('phone_number'),
                wallet_address=wallet_address.lower(),
                referral_code=referral_code,
                referrer=referrer,
                verification_token=generate_verification_token(),
                email_verified=True,
                is_approved=True 
            )
            user.set_unusable_password()
            user.save()
        else:
            # Traditional User
            user = User.objects.create_user(
                username=validated_data['username'],
                email=email,
                password=password,
                phone_number=validated_data.get('phone_number'),
                referral_code=referral_code,
                referrer=referrer,
                verification_token=generate_verification_token()
            )
        
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'phone_number', 'wallet_address', 
                  'is_approved', 'email_verified', 'two_factor_enabled', 'referral_code',
                  'is_staff', 'is_superuser', 'date_joined', 'referrer')
        read_only_fields = ('id', 'email_verified', 'is_approved', 'is_staff', 'is_superuser', 'date_joined')

class Enable2FASerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=6)

class Verify2FASerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    otp_code = serializers.CharField(max_length=6)

class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=100)
