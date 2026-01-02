
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    wallet_address = models.CharField(max_length=42, unique=True, null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    
    # Email and Phone Verification
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, null=True, blank=True)
    
    # 2FA Fields
    two_factor_enabled = models.BooleanField(default=False)
    otp_secret = models.CharField(max_length=32, null=True, blank=True)
    
    # MLM specific fields
    referral_code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    referrer = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone_number']

    def __str__(self):
        return self.email
