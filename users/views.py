from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from .serializers import (
    UserRegistrationSerializer, UserSerializer, 
    Enable2FASerializer, Verify2FASerializer, EmailVerificationSerializer
)
from .utils import (
    send_verification_email, send_otp_email, generate_otp_secret,
    get_otp_uri, generate_qr_code, verify_otp
)

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        from wallet.models import Transaction, SystemSettings
        from decimal import Decimal
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get registration fee info before creating user
        registration_fee_tx_hash = serializer.validated_data.pop('registration_fee_tx_hash', None)
        wallet_address = serializer.validated_data.get('wallet_address')
        
        # Get registration fee amount
        try:
            fee_setting = SystemSettings.objects.get(key='registration_fee')
            registration_fee = Decimal(fee_setting.value)
        except (SystemSettings.DoesNotExist, Exception):
            registration_fee = Decimal('10.00')  # Default fee
        
        # For wallet-based registration, registration fee is required IF fee > 0
        if wallet_address and registration_fee > 0 and not registration_fee_tx_hash:
            return Response({
                'error': 'Registration fee payment is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.save()
        
        # Record registration fee payment if provided
        if registration_fee_tx_hash and wallet_address:
            try:
                Transaction.objects.create(
                    user=user,
                    amount=registration_fee,
                    transaction_type='REGISTRATION_FEE',
                    status='COMPLETED',
                    tx_hash=registration_fee_tx_hash,
                    description=f'Registration fee payment'
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error recording registration fee: {e}")
        
        # Send verification email only if not wallet-based
        if user.email and not user.email.endswith('@wallet.local'):
             send_verification_email(user, user.verification_token)
        
        return Response({
            'message': 'Registration successful.',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

class VerifyEmailView(views.APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        try:
            user = User.objects.get(verification_token=token)
            user.email_verified = True
            user.verification_token = None
            user.save()
            return Response({'message': 'Email verified successfully'})
        except User.DoesNotExist:
            return Response({'error': 'Invalid verification token'}, status=status.HTTP_400_BAD_REQUEST)

class ResendVerificationView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        if user.email_verified:
            return Response({'error': 'Email already verified'}, status=status.HTTP_400_BAD_REQUEST)
        
        from .utils import generate_verification_token
        user.verification_token = generate_verification_token()
        user.save()
        
        send_verification_email(user, user.verification_token)
        return Response({'message': 'Verification email sent'})

class Enable2FAView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        if user.two_factor_enabled:
            return Response({'error': '2FA already enabled'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not user.otp_secret:
            user.otp_secret = generate_otp_secret()
            user.save()
        
        uri = get_otp_uri(user, user.otp_secret)
        qr_code = generate_qr_code(uri)
        
        return Response({
            'qr_code': f'data:image/png;base64,{qr_code}',
            'secret': user.otp_secret
        })
    
    def post(self, request):
        serializer = Enable2FASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        otp_code = serializer.validated_data['otp_code']
        
        if not user.otp_secret:
            return Response({'error': 'Please get QR code first'}, status=status.HTTP_400_BAD_REQUEST)
        
        if verify_otp(user.otp_secret, otp_code):
            user.two_factor_enabled = True
            user.save()
            return Response({'message': '2FA enabled successfully'})
        else:
            return Response({'error': 'Invalid OTP code'}, status=status.HTTP_400_BAD_REQUEST)

class Disable2FAView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        user.two_factor_enabled = False
        user.otp_secret = None
        user.save()
        return Response({'message': '2FA disabled successfully'})

class LoginView(views.APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken
        
        email = request.data.get('email')
        password = request.data.get('password')
        otp_code = request.data.get('otp_code')
        
        user = authenticate(username=email, password=password)
        
        if not user:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.email_verified:
            return Response({'error': 'Please verify your email first'}, status=status.HTTP_403_FORBIDDEN)
        
        if not user.is_approved:
            return Response({'error': 'Your account is pending admin approval'}, status=status.HTTP_403_FORBIDDEN)
        
        if user.two_factor_enabled:
            if not otp_code:
                return Response({
                    'requires_2fa': True,
                    'message': 'Please provide OTP code'
                }, status=status.HTTP_200_OK)
            
            if not verify_otp(user.otp_secret, otp_code):
                return Response({'error': 'Invalid OTP code'}, status=status.HTTP_401_UNAUTHORIZED)
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })

class WalletLoginView(views.APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken
        from eth_account.messages import encode_defunct
        from eth_account import Account
        
        wallet_address = request.data.get('wallet_address', '').lower()
        signature = request.data.get('signature')
        message = request.data.get('message')
        
        if not wallet_address or not signature or not message:
            return Response({'error': 'Missing credentials'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify Signature
            encoded_message = encode_defunct(text=message)
            recovered_address = Account.recover_message(encoded_message, signature=signature)
            
            if recovered_address.lower() != wallet_address:
                return Response({'error': 'Signature verification failed'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get User
            user = User.objects.get(wallet_address__iexact=wallet_address)
            
            if not user.is_approved:
                return Response({'error': 'Account pending approval'}, status=status.HTTP_403_FORBIDDEN)
            
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Login successful',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            })
            
        except User.DoesNotExist:
            return Response({'error': 'Wallet not registered'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Wallet login error: {e}")
            return Response({'error': 'Login failed'}, status=status.HTTP_400_BAD_REQUEST)

class SendOTPEmailView(views.APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            if user.two_factor_enabled:
                send_otp_email(user)
                return Response({'message': 'OTP sent'})
            else:
                return Response({'error': '2FA not enabled'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    def get_object(self):
        return self.request.user
