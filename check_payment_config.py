#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from organizations.models import Gym
from finance.models import FinanceSettings

gym = Gym.objects.get(slug="qombo-arganzuela")
print(f"Gimnasio: {gym.name}")
print(f"Slug: {gym.slug}")

try:
    finance_settings = FinanceSettings.objects.get(gym=gym)
    print("\n=== Configuración de Pagos ===")
    print(f"Stripe habilitado: {finance_settings.stripe_enabled}")
    print(f"Stripe Secret Key: {'✓ Configurada' if finance_settings.stripe_secret_key else '✗ No configurada'}")
    print(f"Stripe Publishable Key: {'✓ Configurada' if finance_settings.stripe_publishable_key else '✗ No configurada'}")
    print(f"\nRedsys habilitado: {finance_settings.redsys_enabled}")
    print(f"Redsys Merchant Code: {'✓ Configurado' if finance_settings.redsys_merchant_code else '✗ No configurado'}")
    print(f"Redsys Terminal: {'✓ Configurado' if finance_settings.redsys_terminal else '✗ No configurado'}")
    print(f"Redsys Secret Key: {'✓ Configurada' if finance_settings.redsys_secret_key else '✗ No configurada'}")
    
    print(f"\n=== Pasarela por Defecto ===")
    print(f"Gateway por defecto: {finance_settings.default_gateway}")
    
except FinanceSettings.DoesNotExist:
    print("\n✗ NO hay configuración de finanzas para este gimnasio")
    print("Creando configuración básica...")
    
    finance_settings = FinanceSettings.objects.create(
        gym=gym,
        stripe_enabled=True,
        stripe_secret_key="sk_test_demo",
        stripe_publishable_key="pk_test_demo",
        redsys_enabled=False,
        default_gateway="stripe"
    )
    print("✓ Configuración creada con Stripe habilitado (claves demo)")
