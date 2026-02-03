# Crear datos de prueba para notificaciones
from gyms.models import Gym
from clients.models import Client, ChatRoom, ChatMessage
from marketing.models import Popup, Advertisement
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

# Buscar gym
gym = Gym.objects.filter(name__icontains='arganzuela').first()
if not gym:
    gym = Gym.objects.filter(name__icontains='qombo').first()

if not gym:
    print("ERROR: No se encontro el gym")
    gyms = list(Gym.objects.values_list('name', flat=True))
    print(f"Gyms disponibles: {gyms}")
else:
    print(f"OK: Gym encontrado: {gym.name}")
    
    # Buscar cliente
    client = Client.objects.filter(gym=gym, first_name__icontains='demo').first()
    if not client:
        client = Client.objects.filter(gym=gym).first()
    
    if not client:
        print("ERROR: No hay clientes en este gym")
    else:
        print(f"OK: Cliente: {client.first_name} {client.last_name}")
        print(f"Email: {client.user.email if hasattr(client, 'user') else 'N/A'}")
        
        # Crear ChatRoom
        chat_room, _ = ChatRoom.objects.get_or_create(client=client, defaults={'gym': gym})
        print(f"OK: ChatRoom ID {chat_room.id}")
        
        # Crear mensajes
        staff = User.objects.filter(is_staff=True).first()
        if not staff:
            staff = User.objects.filter(is_superuser=True).first()
        
        if staff:
            now = timezone.now()
            msgs = [
                (staff, "Hola! Bienvenido", True, 30),
                (staff, "Hay clases hoy?", False, 25),
                (staff, "Si, spinning a las 18:00", True, 20),
                (staff, "Me interesa", False, 15),
            ]
            for sender, msg, is_read, mins_ago in msgs:
                ChatMessage.objects.create(
                    room=chat_room,
                    sender=sender,
                    message=msg,
                    is_read=is_read,
                    created_at=now - timedelta(minutes=mins_ago)
                )
            print(f"OK: {len(msgs)} mensajes creados")
        
        # Crear popups
        now = timezone.now()
        Popup.objects.create(
            gym=gym,
            title="Nueva promocion",
            content="<p>Trae un amigo y obten 1 mes gratis</p>",
            is_active=True,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            audience_type='ALL_ACTIVE'
        )
        Popup.objects.create(
            gym=gym,
            title="Mantenimiento",
            content="<p>Area de pesas cerrada el lunes</p>",
            is_active=True,
            start_date=now,
            end_date=now + timedelta(days=7),
            audience_type='ALL_CLIENTS'
        )
        Popup.objects.create(
            gym=gym,
            title="Nuevas clases",
            content="<p>CrossFit y Pilates disponibles</p>",
            is_active=True,
            start_date=now,
            end_date=now + timedelta(days=15),
            target_client=client,
            audience_type='ALL_ACTIVE'
        )
        print("OK: 3 popups creados")
        
        # Crear anuncios
        Advertisement.objects.create(
            gym=gym,
            title="Spinning Especial",
            content="Sabado 10:00 AM",
            position="HOME_HERO",
            is_active=True,
            start_date=now,
            end_date=now + timedelta(days=5),
            cta_text="Reservar",
            cta_action="BOOK_CLASS",
            target_screens={"portal": ["home"]}
        )
        Advertisement.objects.create(
            gym=gym,
            title="Nutricion Deportiva",
            content="Consulta gratuita",
            position="HOME_BANNER",
            is_active=True,
            start_date=now,
            end_date=now + timedelta(days=14),
            cta_text="Mas info",
            cta_action="EXTERNAL_LINK",
            cta_url="https://example.com",
            target_screens={"portal": ["home"]}
        )
        print("OK: 2 anuncios creados")
        
        print("\n" + "="*50)
        print("DATOS CREADOS EXITOSAMENTE")
        print("="*50)
        print(f"URL: http://127.0.0.1:8000/portal/notifications/")
        print(f"Login: {client.user.email if hasattr(client, 'user') else 'N/A'}")
