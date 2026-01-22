from django.db import models
from django.utils import timezone
from datetime import timedelta

class PasswordResetToken(models.Model):
    """
    Stores temporary password reset codes.
    Codes are valid for 15 minutes.
    """
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def is_valid(self):
        """Check if token is still valid (not used and not expired)"""
        if self.used:
            return False
        expiry_time = self.created_at + timedelta(minutes=15)
        return timezone.now() < expiry_time
    
    def __str__(self):
        return f"{self.email} - {self.code} ({'used' if self.used else 'active'})"
