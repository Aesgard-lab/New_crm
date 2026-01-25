"""
Script para crear datos de prueba para el sistema de notificaciones del portal
"""
from django.utils import timezone
from datetime import timedelta
from gyms.models import Gym
from clients.models import Client, ChatRoom, ChatMessage
from marketing.models import Popup, Advertisement
from django.contrib.auth import get_user_model

User = get_user_model()

def create_test_data():
    print("Buscando gym 'Qombo Arganzuela'...")
    try:
        gym = Gym.objects.filter(name__icontains='arganzuela').first()
        if not gym:
            gym = Gym.objects.filter(name__icontains='qombo').first()
        
        if not gym:
            print("ERROR: No se encontro el gym 'Qombo Arganzuela'")
            print(f"Gyms disponibles: {list(Gym.objects.values_list('name', flat=True))}")
            return
        
        print(f"OK: Gym encontrado: {gym.name} (ID: {gym.id})")
        
        print("\nBuscando cliente 'demo cliente'...")
        client = Client.objects.filter(
            gym=gym,
            first_name__icontains='demo'
        ).first()
        
        if not client:
            client = Client.objects.filter(gym=gym).first()
        
        if not client:
            print("ERROR: No se encontro ningun cliente en este gym")
            return
        
        print(f"OK: Cliente encontrado: {client.first_name} {client.last_name} (ID: {client.id})")
        print(f"   Email: {client.user.email if hasattr(client, 'user') else 'N/A'}")
        
        # Crear ChatRoom si no existe
        print("\nCreando/Verificando ChatRoom...")
        chat_room, created = ChatRoom.objects.get_or_create(
            client=client,
            defaults={'gym': gym}
        )
        if created:
            print(f"OK: ChatRoom creado (ID: {chat_room.id})")
        else:
            print(f"OK: ChatRoom existente (ID: {chat_room.id})")
        
        # Crear mensajes de chat (algunos del staff, algunos del cliente)
        print("\nCreando mensajes de chat...")
        staff_user = User.objects.filter(is_staff=True).first()
        client_user = client.user if hasattr(client, 'user') else None
        
        if not staff_user:
            print("WARN: No se encontro usuario staff, usando superuser...")
            staff_user = User.objects.filter(is_superuser=True).first()
        
        if staff_user:
            messages_data = [
                (staff_user, "Hola! Bienvenido a nuestro sistema de chat.", True),
                (client_user if client_user else staff_user, "Gracias, hay clases disponibles hoy?", False),
                (staff_user, "Si, tenemos spinning a las 18:00 y yoga a las 19:30.", True),
                (staff_user, "Te gustaria reservar alguna?", False),
                (client_user if client_user else staff_user, "Me interesa la de yoga.", False),
            ]
            
            for i, (sender, msg, is_read) in enumerate(messages_data):
                created_at = timezone.now() - timedelta(minutes=30-i*5)
                ChatMessage.objects.create(
                    room=chat_room,
                    sender=sender,
                    message=msg,
                    is_read=is_read,
                    created_at=created_at
                )
            print(f"OK: {len(messages_data)} mensajes de chat creados")
        else:
            print("ERROR: No se pudo crear mensajes (sin usuarios)")
        
        # Crear Popups
        print("\nCreando popups...")
        now = timezone.now()
        
        popup1 = Popup.objects.create(
            gym=gym,
            title="Nueva promocion!",
            content="<p>Trae un amigo y obten <strong>1 mes gratis</strong>. Promocion valida hasta fin de mes.</p>",
            is_active=True,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            audience_type='ALL_ACTIVE'
        )
        print(f"OK: Popup promocion creado (ID: {popup1.id})")
        
        popup2 = Popup.objects.create(
            gym=gym,
            title="Mantenimiento programado",
            content="<p>El area de pesas estara cerrada el proximo lunes por mantenimiento.</p>",
            is_active=True,
            start_date=now - timedelta(hours=2),
            end_date=now + timedelta(days=7),
            audience_type='ALL_CLIENTS'
        )
        print(f"OK: Popup mantenimiento creado (ID: {popup2.id})")
        
        popup3 = Popup.objects.create(
            gym=gym,
            title="Nuevas clases disponibles",
            content="<p>Ya puedes reservar nuestras nuevas clases de <strong>CrossFit</strong> y <strong>Pilates</strong>.</p>",
            is_active=True,
            start_date=now,
            end_date=now + timedelta(days=15),
            target_client=client,
            audience_type='ALL_ACTIVE'
        )
        print(f"OK: Popup personalizado creado (ID: {popup3.id})")
        
        # Crear Advertisements
        print("\nCreando anuncios...")
        
        ad1 = Advertisement.objects.create(
            gym=gym,
            title="Clase Especial de Spinning",
            content="Este sabado a las 10:00 AM. Inscribete ya!",
            position="HOME_HERO",
            is_active=True,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=5),
            cta_text="Reservar ahora",
            cta_action="BOOK_CLASS",
            target_screens={"portal": ["home", "bookings"]}
        )
        print(f"OK: Anuncio spinning creado (ID: {ad1.id})")
        
        ad2 = Advertisement.objects.create(
            gym=gym,
            title="Nutricion Deportiva",
            content="Consulta gratuita con nuestro nutricionista. Plazas limitadas.",
            position="HOME_BANNER",
            is_active=True,
            start_date=now,
            end_date=now + timedelta(days=14),
            cta_text="Mas informacion",
            cta_action="EXTERNAL_LINK",
            cta_url="https://example.com/nutricion",
            target_screens={"portal": ["home"]}
        )
        print(f"OK: Anuncio nutricion creado (ID: {ad2.id})")
        
        ad3 = Advertisement.objects.create(
            gym=gym,
            title="Descuento en Suplementos",
            content="20% de descuento en toda la tienda hasta el domingo.",
            position="SIDEBAR",
            is_active=True,
            start_date=now - timedelta(hours=6),
            end_date=now + timedelta(days=3),
            cta_text="Ver tienda",
            cta_action="SHOP",
            target_screens={"portal": ["home", "shop"]}
        )
        print(f"OK: Anuncio tienda creado (ID: {ad3.id})")
        
        print("\n" + "="*60)
        print("DATOS DE PRUEBA CREADOS EXITOSAMENTE")
        print("="*60)
        print(f"\nResumen:")
        print(f"   - Cliente: {client.first_name} {client.last_name}")
        print(f"   - Gym: {gym.name}")
        print(f"   - Mensajes de chat: {ChatMessage.objects.filter(room=chat_room).count()}")
        print(f"   - Mensajes no leidos: {ChatMessage.objects.filter(room=chat_room, is_read=False).exclude(sender=client.user if hasattr(client, 'user') else None).count()}")
        print(f"   - Popups activos: {Popup.objects.filter(gym=gym, is_active=True).count()}")
        print(f"   - Anuncios activos: {Advertisement.objects.filter(gym=gym, is_active=True).count()}")
        print(f"\nURL para probar: http://127.0.0.1:8000/portal/notifications/")
        print(f"   Inicia sesion con: {client.user.email if hasattr(client, 'user') else 'Usuario del cliente'}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    create_test_data()
