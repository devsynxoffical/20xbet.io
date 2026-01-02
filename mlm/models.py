from django.db import models
from django.conf import settings

class MLMLevel(models.Model):
    level = models.IntegerField(unique=True)
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage for this level (e.g., 10 for 10%)")

    def __str__(self):
        return f"Level {self.level} - {self.name}"

class UserLevel(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mlm_level')
    current_level = models.ForeignKey(MLMLevel, on_delete=models.SET_NULL, null=True, blank=True)
    activated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.current_level}"

class Commission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='commissions_received')
    source_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='commissions_generated')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    level = models.IntegerField(help_text="Generation level (1-5)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} to {self.user.username} from {self.source_user.username} (L{self.level})"
