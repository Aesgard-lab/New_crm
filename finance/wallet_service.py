"""
Servicio de Monedero Virtual (Wallet) para clientes.
Gestiona saldos, recargas, pagos y bonificaciones.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import ClientWallet, WalletTransaction, WalletSettings, PaymentMethod


class WalletService:
    """
    Servicio central para operaciones del monedero del cliente.
    """
    
    @staticmethod
    def get_or_create_wallet(client, gym):
        """
        Obtiene o crea el monedero de un cliente.
        Aplica configuraciones por defecto del gym.
        """
        wallet, created = ClientWallet.objects.get_or_create(
            client=client,
            gym=gym,
            defaults={
                'balance': Decimal('0.00'),
                'is_active': True,
            }
        )
        
        if created:
            # Aplicar configuraciones por defecto del gym
            try:
                settings = gym.wallet_settings
                wallet.allow_negative = settings.allow_negative_default
                wallet.negative_limit = settings.default_negative_limit
                wallet.save()
            except WalletSettings.DoesNotExist:
                pass
        
        return wallet, created
    
    @staticmethod
    def get_wallet_settings(gym):
        """Obtiene la configuración de monedero del gym, creándola si no existe."""
        settings, created = WalletSettings.objects.get_or_create(
            gym=gym,
            defaults={
                'wallet_enabled': False,
                'topup_preset_amounts': [20, 50, 100, 200],
            }
        )
        return settings
    
    @staticmethod
    def is_wallet_enabled(gym):
        """Verifica si el sistema de monedero está habilitado para el gym."""
        try:
            return gym.wallet_settings.wallet_enabled
        except WalletSettings.DoesNotExist:
            return False
    
    @staticmethod
    @transaction.atomic
    def topup(wallet, amount, payment_method=None, created_by=None, description="", notes=""):
        """
        Recarga el monedero del cliente.
        Aplica bonificación si corresponde.
        
        Returns:
            tuple: (WalletTransaction de recarga, WalletTransaction de bonus o None)
        """
        amount = Decimal(str(amount))
        
        if amount <= 0:
            raise ValidationError("El monto de recarga debe ser positivo")
        
        # Verificar límites
        settings = WalletService.get_wallet_settings(wallet.gym)
        
        if amount < settings.min_topup_amount:
            raise ValidationError(f"La recarga mínima es {settings.min_topup_amount}€")
        
        if settings.max_topup_amount > 0 and amount > settings.max_topup_amount:
            raise ValidationError(f"La recarga máxima es {settings.max_topup_amount}€")
        
        balance_before = wallet.balance
        wallet.balance += amount
        wallet.total_topups += amount
        wallet.last_transaction_at = timezone.now()
        wallet.save()
        
        # Crear transacción de recarga
        topup_tx = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.TransactionType.TOPUP,
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            description=description or f"Recarga de {amount}€",
            topup_method=payment_method,
            created_by=created_by,
            notes=notes,
        )
        
        # Calcular y aplicar bonificación
        bonus_tx = None
        bonus_amount = settings.calculate_bonus(amount)
        
        if bonus_amount > 0:
            balance_before_bonus = wallet.balance
            wallet.balance += Decimal(str(bonus_amount))
            wallet.save()
            
            bonus_tx = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransaction.TransactionType.TOPUP_BONUS,
                amount=Decimal(str(bonus_amount)),
                balance_before=balance_before_bonus,
                balance_after=wallet.balance,
                description=f"Bonificación por recarga de {amount}€",
                created_by=created_by,
            )
        
        return topup_tx, bonus_tx
    
    @staticmethod
    @transaction.atomic
    def pay(wallet, amount, order=None, external_ref="", created_by=None, description=""):
        """
        Realiza un pago desde el monedero.
        
        Returns:
            WalletTransaction
        """
        amount = Decimal(str(amount))
        
        if amount <= 0:
            raise ValidationError("El monto a pagar debe ser positivo")
        
        if not wallet.can_pay(amount):
            raise ValidationError(
                f"Saldo insuficiente. Disponible: {wallet.available_balance}€, "
                f"Requerido: {amount}€"
            )
        
        balance_before = wallet.balance
        wallet.balance -= amount
        wallet.total_spent += amount
        wallet.last_transaction_at = timezone.now()
        wallet.save()
        
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.TransactionType.PAYMENT,
            amount=-amount,  # Negativo porque es un gasto
            balance_before=balance_before,
            balance_after=wallet.balance,
            description=description or "Pago con saldo",
            order=order,
            external_payment_ref=external_ref,
            created_by=created_by,
        )
        
        return tx
    
    @staticmethod
    @transaction.atomic
    def refund(wallet, amount, order=None, external_ref="", created_by=None, description=""):
        """
        Devuelve dinero al monedero del cliente.
        
        Returns:
            WalletTransaction
        """
        amount = Decimal(str(amount))
        
        if amount <= 0:
            raise ValidationError("El monto a devolver debe ser positivo")
        
        balance_before = wallet.balance
        wallet.balance += amount
        wallet.last_transaction_at = timezone.now()
        wallet.save()
        
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.TransactionType.REFUND,
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            description=description or "Devolución al saldo",
            order=order,
            external_payment_ref=external_ref,
            created_by=created_by,
        )
        
        return tx
    
    @staticmethod
    @transaction.atomic
    def adjust(wallet, amount, reason="", created_by=None, notes=""):
        """
        Ajuste manual del saldo (positivo o negativo).
        
        Returns:
            WalletTransaction
        """
        amount = Decimal(str(amount))
        
        if amount == 0:
            raise ValidationError("El ajuste no puede ser cero")
        
        balance_before = wallet.balance
        wallet.balance += amount
        wallet.last_transaction_at = timezone.now()
        wallet.save()
        
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.TransactionType.ADJUSTMENT,
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            description=reason or ("Ajuste positivo" if amount > 0 else "Ajuste negativo"),
            created_by=created_by,
            notes=notes,
        )
        
        return tx
    
    @staticmethod
    @transaction.atomic
    def add_referral_bonus(wallet, amount, description="", created_by=None):
        """
        Añade bonificación por referido al monedero.
        
        Returns:
            WalletTransaction
        """
        amount = Decimal(str(amount))
        
        if amount <= 0:
            raise ValidationError("La bonificación debe ser positiva")
        
        balance_before = wallet.balance
        wallet.balance += amount
        wallet.last_transaction_at = timezone.now()
        wallet.save()
        
        tx = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.TransactionType.REFERRAL_BONUS,
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            description=description or "Bonus por referido",
            created_by=created_by,
        )
        
        return tx
    
    @staticmethod
    def get_balance(client, gym):
        """Obtiene el saldo actual del cliente."""
        try:
            wallet = ClientWallet.objects.get(client=client, gym=gym)
            return wallet.balance
        except ClientWallet.DoesNotExist:
            return Decimal('0.00')
    
    @staticmethod
    def get_transaction_history(wallet, limit=50):
        """Obtiene el historial de transacciones."""
        return wallet.transactions.select_related(
            'order', 'created_by', 'topup_method'
        )[:limit]
    
    @staticmethod
    def get_summary(wallet):
        """Obtiene un resumen del monedero."""
        from django.db.models import Sum, Count
        
        transactions = wallet.transactions.all()
        
        # Totales por tipo
        topups = transactions.filter(
            transaction_type__in=['TOPUP', 'TOPUP_BONUS', 'REFERRAL_BONUS', 'REFUND']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        payments = abs(transactions.filter(
            transaction_type='PAYMENT'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'))
        
        # Transacciones del mes
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month = transactions.filter(created_at__gte=month_start)
        
        return {
            'balance': wallet.balance,
            'available_balance': wallet.available_balance,
            'total_topups': wallet.total_topups,
            'total_spent': wallet.total_spent,
            'total_inflows': topups,
            'total_outflows': payments,
            'transaction_count': transactions.count(),
            'transactions_this_month': this_month.count(),
            'spent_this_month': abs(this_month.filter(
                transaction_type='PAYMENT'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')),
            'is_negative': wallet.is_negative,
            'allow_negative': wallet.allow_negative,
            'negative_limit': wallet.negative_limit,
        }
    
    @staticmethod
    def process_partial_payment(wallet, total_amount, use_full_balance=True):
        """
        Procesa un pago parcial con el monedero.
        Retorna cuánto se puede pagar con saldo y cuánto queda pendiente.
        
        Returns:
            tuple: (wallet_amount, remaining_amount)
        """
        total_amount = Decimal(str(total_amount))
        available = wallet.available_balance
        
        if available <= 0:
            return Decimal('0.00'), total_amount
        
        if use_full_balance:
            wallet_amount = min(available, total_amount)
        else:
            wallet_amount = total_amount if available >= total_amount else Decimal('0.00')
        
        remaining = total_amount - wallet_amount
        
        return wallet_amount, remaining
    
    @staticmethod
    def get_or_create_wallet_payment_method(gym):
        """
        Obtiene o crea el método de pago 'Saldo de Cuenta' para el gym.
        """
        method, created = PaymentMethod.objects.get_or_create(
            gym=gym,
            provider_code='WALLET',
            defaults={
                'name': 'Saldo de Cuenta',
                'description': 'Pago con saldo del monedero virtual',
                'is_cash': False,
                'is_active': True,
                'available_for_online': True,
                'gateway': 'NONE',
                'display_order': 1,
            }
        )
        return method


# Funciones de conveniencia
def wallet_enabled_for_gym(gym):
    """Atajo para verificar si el monedero está habilitado."""
    return WalletService.is_wallet_enabled(gym)


def get_client_wallet(client, gym, create=True):
    """Atajo para obtener el monedero de un cliente."""
    if create:
        wallet, _ = WalletService.get_or_create_wallet(client, gym)
        return wallet
    else:
        try:
            return ClientWallet.objects.get(client=client, gym=gym)
        except ClientWallet.DoesNotExist:
            return None
