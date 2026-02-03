"""
API de Monedero Virtual para la App Móvil.
Permite consultar saldo, historial y recargar desde la app.
"""
from decimal import Decimal
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from finance.models import ClientWallet, WalletTransaction, WalletSettings
from finance.wallet_service import WalletService


class WalletStatusView(APIView):
    """
    GET: Obtener estado del monedero y configuración.
    Retorna si está habilitado, saldo, límites, etc.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = getattr(request.user, 'client', None)
        if not client:
            return Response(
                {"error": "No se encontró el perfil de cliente"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        gym = client.gym
        
        # Verificar si el monedero está habilitado
        if not WalletService.is_wallet_enabled(gym):
            return Response({
                "enabled": False,
                "show_in_app": False,
            })
        
        settings = WalletService.get_wallet_settings(gym)
        
        # Verificar si debe mostrarse en la app
        if not settings.show_in_app:
            return Response({
                "enabled": True,
                "show_in_app": False,
            })
        
        # Obtener o crear monedero
        wallet, _ = WalletService.get_or_create_wallet(client, gym)
        
        return Response({
            "enabled": True,
            "show_in_app": True,
            "wallet": {
                "balance": str(wallet.balance),
                "balance_display": wallet.get_balance_display(),
                "available_balance": str(wallet.available_balance),
                "is_active": wallet.is_active,
                "is_negative": wallet.is_negative,
                "allow_negative": wallet.allow_negative,
                "negative_limit": str(wallet.negative_limit),
                "total_topups": str(wallet.total_topups),
                "total_spent": str(wallet.total_spent),
                "last_activity": wallet.last_transaction_at.isoformat() if wallet.last_transaction_at else None,
            },
            "settings": {
                "allow_online_topup": settings.allow_online_topup,
                "min_topup": str(settings.min_topup_amount),
                "max_topup": str(settings.max_topup_amount),
                "preset_amounts": settings.topup_preset_amounts or [20, 50, 100, 200],
                "topup_bonus_enabled": settings.topup_bonus_enabled,
                "topup_bonus_type": settings.topup_bonus_type,
                "topup_bonus_percent": str(settings.topup_bonus_percent),
                "topup_bonus_min_amount": str(settings.topup_bonus_min_amount),
            }
        })


class WalletBalanceView(APIView):
    """
    GET: Obtener solo el saldo (para badges/widgets rápidos).
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = getattr(request.user, 'client', None)
        if not client:
            return Response({"balance": "0.00", "show": False})
        
        gym = client.gym
        
        if not WalletService.is_wallet_enabled(gym):
            return Response({"balance": "0.00", "show": False})
        
        try:
            settings = gym.wallet_settings
            if not settings.show_in_app:
                return Response({"balance": "0.00", "show": False})
        except WalletSettings.DoesNotExist:
            return Response({"balance": "0.00", "show": False})
        
        balance = WalletService.get_balance(client, gym)
        
        return Response({
            "balance": str(balance),
            "balance_display": f"{balance:.2f}€" if balance >= 0 else f"{balance:.2f}€",
            "show": True,
            "is_positive": balance > 0,
            "is_negative": balance < 0,
        })


class WalletHistoryView(APIView):
    """
    GET: Obtener historial de transacciones del monedero.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = getattr(request.user, 'client', None)
        if not client:
            return Response(
                {"error": "No se encontró el perfil de cliente"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        gym = client.gym
        
        if not WalletService.is_wallet_enabled(gym):
            return Response({"transactions": []})
        
        try:
            wallet = ClientWallet.objects.get(client=client, gym=gym)
        except ClientWallet.DoesNotExist:
            return Response({"transactions": []})
        
        # Obtener parámetros de paginación
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        offset = (page - 1) * per_page
        
        transactions = wallet.transactions.order_by('-created_at')[offset:offset + per_page]
        total = wallet.transactions.count()
        
        data = []
        for tx in transactions:
            data.append({
                "id": tx.pk,
                "type": tx.transaction_type,
                "type_display": tx.get_transaction_type_display(),
                "amount": str(tx.amount),
                "balance_after": str(tx.balance_after),
                "description": tx.description,
                "is_credit": tx.is_credit,
                "is_debit": tx.is_debit,
                "created_at": tx.created_at.isoformat(),
                "icon": self._get_icon(tx.transaction_type),
            })
        
        return Response({
            "transactions": data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "has_more": offset + per_page < total,
        })
    
    def _get_icon(self, tx_type):
        icons = {
            'TOPUP': '💳',
            'TOPUP_BONUS': '🎁',
            'PAYMENT': '🛒',
            'REFUND': '↩️',
            'ADJUSTMENT': '⚖️',
            'REFERRAL_BONUS': '👥',
            'POINTS_CONVERSION': '🏆',
            'EXPIRY': '⏰',
        }
        return icons.get(tx_type, '📝')


class WalletTopupView(APIView):
    """
    POST: Iniciar recarga del monedero (requiere integración con pasarela).
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        client = getattr(request.user, 'client', None)
        if not client:
            return Response(
                {"error": "No se encontró el perfil de cliente"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        gym = client.gym
        
        if not WalletService.is_wallet_enabled(gym):
            return Response(
                {"error": "El sistema de monedero no está habilitado"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        settings = WalletService.get_wallet_settings(gym)
        
        if not settings.allow_online_topup:
            return Response(
                {"error": "La recarga online no está habilitada"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        amount = request.data.get('amount')
        if not amount:
            return Response(
                {"error": "Debe especificar el monto a recargar"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return Response(
                {"error": "Monto inválido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar límites
        if amount < settings.min_topup_amount:
            return Response(
                {"error": f"La recarga mínima es {settings.min_topup_amount}€"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if settings.max_topup_amount > 0 and amount > settings.max_topup_amount:
            return Response(
                {"error": f"La recarga máxima es {settings.max_topup_amount}€"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calcular bonificación para mostrar al usuario
        bonus = settings.calculate_bonus(amount)
        total_to_receive = amount + Decimal(str(bonus))
        
        # TODO: Integrar con Stripe/Redsys para crear sesión de pago
        # Por ahora devolvemos info de la recarga
        
        return Response({
            "amount": str(amount),
            "bonus": str(bonus),
            "total_to_receive": str(total_to_receive),
            "message": f"Recibirás {total_to_receive}€ en tu monedero",
            # "payment_url": payment_session_url,  # URL de Stripe Checkout
        })


class WalletBonusCalculatorView(APIView):
    """
    GET: Calcular bonificación para un monto de recarga.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        client = getattr(request.user, 'client', None)
        if not client:
            return Response({"bonus": "0.00"})
        
        gym = client.gym
        
        if not WalletService.is_wallet_enabled(gym):
            return Response({"bonus": "0.00"})
        
        amount = request.GET.get('amount')
        if not amount:
            return Response({"bonus": "0.00"})
        
        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return Response({"bonus": "0.00"})
        
        settings = WalletService.get_wallet_settings(gym)
        bonus = settings.calculate_bonus(amount)
        
        return Response({
            "amount": str(amount),
            "bonus": str(bonus),
            "total": str(amount + Decimal(str(bonus))),
            "bonus_percent": f"{settings.topup_bonus_percent}%" if settings.topup_bonus_type == 'PERCENT' else None,
        })
