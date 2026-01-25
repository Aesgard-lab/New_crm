#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from organizations.models import Gym
from finance.models import FinanceSettings

gym = Gym.objects.get(slug="qombo-arganzuela")
print(f"Gimnasio: {gym.name}")

try:
    fs = FinanceSettings.objects.get(gym=gym)
    print("\n=== Configuración Actual ===")
    print(f"Stripe Public Key: {fs.stripe_public_key[:20] if fs.stripe_public_key else '✗ No configurada'}...")
    print(f"Stripe Secret Key: {fs.stripe_secret_key[:20] if fs.stripe_secret_key else '✗ No configurada'}...")
    print(f"Redsys Merchant Code: {fs.redsys_merchant_code if fs.redsys_merchant_code else '✗ No configurado'}")
    print(f"App Gateway Strategy: {fs.app_gateway_strategy}")
    print(f"POS Gateway Strategy: {fs.pos_gateway_strategy}")
    print(f"\nhas_stripe: {fs.has_stripe}")
    print(f"has_redsys: {fs.has_redsys}")
    
    if not fs.has_stripe and not fs.has_redsys:
        print("\n⚠️  No hay ninguna pasarela configurada!")
        print("Configurando Stripe con claves de prueba...")
        fs.stripe_public_key = "pk_test_51PZa8bRqpG8KU4N4F6h0z8CK1f2g3h4"
        fs.stripe_secret_key = "sk_test_51PZa8bRqpG8KU4N4DEMO_SECRET_KEY"
        fs.app_gateway_strategy = "STRIPE_ONLY"
        fs.pos_gateway_strategy = "STRIPE_ONLY"
        fs.save()
        print("✓ Stripe configurado")
    
except FinanceSettings.DoesNotExist:
    print("\n✗ NO existe FinanceSettings para este gimnasio")
    print("Creando configuración...")
    fs = FinanceSettings.objects.create(
        gym=gym,
        stripe_public_key="pk_test_51PZa8bRqpG8KU4N4F6h0z8CK1f2g3h4",
        stripe_secret_key="sk_test_51PZa8bRqpG8KU4N4DEMO_SECRET_KEY",
        app_gateway_strategy="STRIPE_ONLY",
        pos_gateway_strategy="STRIPE_ONLY",
        currency="EUR"
    )
    print("✓ FinanceSettings creado con Stripe")

print(f"\n✓ Pasarela principal (app): {fs.get_primary_gateway('app')}")
