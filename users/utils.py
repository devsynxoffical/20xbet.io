import secrets
import pyotp
from django.core.mail import send_mail
from django.conf import settings
from io import BytesIO
import qrcode
import base64

def generate_verification_token():
    """Generate a random verification token"""
    return secrets.token_urlsafe(32)

def generate_otp_secret():
    """Generate a random OTP secret for 2FA"""
    return pyotp.random_base32()

def verify_otp(secret, token):
    """Verify OTP token"""
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)

def get_otp_uri(user, secret):
    """Get OTP provisioning URI for QR code"""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name='MLM System'
    )

def generate_qr_code(uri):
    """Generate QR code image as base64 string"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()

def send_verification_email(user, token):
    """Send email verification link"""
    verification_link = f"http://localhost:5173/verify-email?token={token}"
    subject = 'Verify your email address'
    message = f'''
    Hi {user.username},
    
    Please verify your email address by clicking the link below:
    {verification_link}
    
    If you didn't create an account, please ignore this email.
    
    Best regards,
    MLM System Team
    '''
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

def send_otp_email(user):
    """Send OTP code via email"""
    if not user.otp_secret:
        return False
    
    totp = pyotp.TOTP(user.otp_secret)
    otp_code = totp.now()
    
    subject = 'Your 2FA Code'
    message = f'''
    Hi {user.username},
    
    Your 2FA verification code is: {otp_code}
    
    This code will expire in 30 seconds.
    
    If you didn't request this code, please secure your account immediately.
    
    Best regards,
    MLM System Team
    '''
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    return True
