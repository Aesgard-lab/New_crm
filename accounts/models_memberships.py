from django.db import models
from django.conf import settings


class Permission(models.Model):
    """
    Permisos "clickables" a nivel de gimnasio.
    Ejemplos:
      - clients.view
      - clients.create
      - staff.manage
      - marketing.view
    """
    code = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=150)

    def __str__(self):
        return self.code


class FranchiseMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="franchise_memberships")
    franchise = models.ForeignKey("organizations.Franchise", on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OWNER)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "franchise", "role")

    def __str__(self):
        return f"{self.user} · {self.franchise} · {self.role}"


class GymMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STAFF = "STAFF", "Staff"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="gym_memberships")
    gym = models.ForeignKey("organizations.Gym", on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices)

    # permisos clickables (solo aplica a staff; a admin le damos todo)
    permissions = models.ManyToManyField(Permission, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "gym")

    def __str__(self):
        return f"{self.user} · {self.gym} · {self.role}"
