from django.db import models


class Franchise(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Gym(models.Model):
    name = models.CharField(max_length=200, help_text="Nombre interno/sistema")
    
    # Branding
    commercial_name = models.CharField(max_length=200, blank=True, help_text="Nombre Comercial (Público)")
    brand_color = models.CharField(max_length=7, default="#0f172a", help_text="Color corporativo en Hex (ej: #0f172a)")
    logo = models.ImageField(upload_to='gym_logos/', blank=True, null=True)
    
    # Fiscal Data (for Invoices)
    legal_name = models.CharField(max_length=200, blank=True, help_text="Razón Social / Nombre de Empresa")
    tax_id = models.CharField(max_length=20, blank=True, help_text="CIF / NIF")
    
    # Contact & Address
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    province = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="España", blank=True)
    
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Social Media
    instagram = models.URLField(blank=True, help_text="URL completa (https://instagram.com/...)")
    facebook = models.URLField(blank=True, help_text="URL completa")
    tiktok = models.URLField(blank=True, help_text="URL completa")
    youtube = models.URLField(blank=True, help_text="URL completa")

    franchise = models.ForeignKey(
        Franchise,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gyms",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("franchise", "name")  # nombre único dentro de una franquicia

    def __str__(self):
        return self.commercial_name or self.name
