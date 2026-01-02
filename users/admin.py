from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils import timezone
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'phone_number', 'is_approved', 'email_verified', 'two_factor_enabled', 'action_buttons')
    search_fields = ('email', 'username', 'phone_number')
    list_filter = ('is_approved', 'email_verified', 'two_factor_enabled', 'is_staff')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('MLM Info', {'fields': ('phone_number', 'wallet_address', 'referral_code', 'referrer')}),
        ('Verification', {'fields': ('is_approved', 'email_verified', 'phone_verified', 'verification_token')}),
        ('2FA', {'fields': ('two_factor_enabled', 'otp_secret')}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('email', 'phone_number', 'wallet_address')}),
    )
    
    def action_buttons(self, obj):
        if not obj.is_approved and obj.email_verified:
            return format_html(
                '<a class="button" href="/admin/users/user/{}/approve/">Approve</a> '
                '<a class="button" href="/admin/users/user/{}/reject/">Reject</a>',
                obj.pk, obj.pk
            )
        elif obj.is_approved:
            return format_html('<span style="color: green;">✓ Approved</span>')
        else:
            return format_html('<span style="color: orange;">Email not verified</span>')
    action_buttons.short_description = 'Actions'
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/approve/', self.admin_site.admin_view(self.approve_user), name='approve-user'),
            path('<int:pk>/reject/', self.admin_site.admin_view(self.reject_user), name='reject-user'),
        ]
        return custom_urls + urls
    
    def approve_user(self, request, pk):
        from django.shortcuts import redirect
        from django.contrib import messages
        from wallet.models import Wallet
        
        user = User.objects.get(pk=pk)
        user.is_approved = True
        user.save()
        
        # Create wallet for user if doesn't exist
        Wallet.objects.get_or_create(user=user)
        
        messages.success(request, f'User {user.email} approved successfully')
        return redirect('admin:users_user_changelist')
    
    def reject_user(self, request, pk):
        from django.shortcuts import redirect
        from django.contrib import messages
        
        user = User.objects.get(pk=pk)
        user.is_approved = False
        user.save()
        
        messages.success(request, f'User {user.email} rejected')
        return redirect('admin:users_user_changelist')
