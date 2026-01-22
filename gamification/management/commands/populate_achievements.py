from django.core.management.base import BaseCommand
from gamification.models import Achievement
from organizations.models import Gym


class Command(BaseCommand):
    help = 'Crea los logros predefinidos del sistema de gamificación para todos los gimnasios'

    def handle(self, *args, **options):
        gyms = Gym.objects.all()
        
        if not gyms.exists():
            self.stdout.write(
                self.style.ERROR('❌ No hay gimnasios en la base de datos')
            )
            return
        achievements = [
            # Logros de asistencia
            {
                'code': 'first_visit',
                'name': '¡Primer Día!',
                'description': 'Completaste tu primera visita al gimnasio',
                'icon': '🎉',
                'requirement_type': 'total_visits',
                'requirement_value': 1,
                'xp_reward': 10,
                'category': 'ATTENDANCE',
            },
            {
                'code': 'visits_10',
                'name': 'Visitante Regular',
                'description': 'Alcanzaste 10 visitas al gimnasio',
                'icon': '💪',
                'requirement_type': 'total_visits',
                'requirement_value': 10,
                'xp_reward': 50,
                'category': 'ATTENDANCE',
            },
            {
                'code': 'visits_25',
                'name': 'Comprometido',
                'description': 'Alcanzaste 25 visitas al gimnasio',
                'icon': '🔥',
                'requirement_type': 'total_visits',
                'requirement_value': 25,
                'xp_reward': 100,
                'category': 'ATTENDANCE',
            },
            {
                'code': 'visits_50',
                'name': 'Entusiasta del Fitness',
                'description': 'Alcanzaste 50 visitas al gimnasio',
                'icon': '⭐',
                'requirement_type': 'total_visits',
                'requirement_value': 50,
                'xp_reward': 200,
                'category': 'ATTENDANCE',
            },
            {
                'code': 'visits_100',
                'name': 'Centenario',
                'description': '¡100 visitas! Eres una leyenda',
                'icon': '👑',
                'requirement_type': 'total_visits',
                'requirement_value': 100,
                'xp_reward': 500,
                'category': 'ATTENDANCE',
            },
            
            # Logros de racha
            {
                'code': 'streak_3',
                'name': 'Ritmo Constante',
                'description': 'Mantén una racha de 3 días consecutivos',
                'icon': '🔄',
                'requirement_type': 'current_streak',
                'requirement_value': 3,
                'xp_reward': 30,
                'category': 'STREAK',
            },
            {
                'code': 'streak_7',
                'name': 'Semana Perfecta',
                'description': 'Mantén una racha de 7 días consecutivos',
                'icon': '📅',
                'requirement_type': 'current_streak',
                'requirement_value': 7,
                'xp_reward': 100,
                'category': 'STREAK',
            },
            {
                'code': 'streak_14',
                'name': 'Quincena Imparable',
                'description': 'Mantén una racha de 14 días consecutivos',
                'icon': '🚀',
                'requirement_type': 'current_streak',
                'requirement_value': 14,
                'xp_reward': 250,
                'category': 'STREAK',
            },
            {
                'code': 'streak_30',
                'name': 'Mes Legendario',
                'description': '¡30 días seguidos! Increíble dedicación',
                'icon': '💎',
                'requirement_type': 'current_streak',
                'requirement_value': 30,
                'xp_reward': 500,
                'category': 'STREAK',
            },
            {
                'code': 'longest_streak_30',
                'name': 'Récord Personal',
                'description': 'Tu mejor racha alcanzó 30 días',
                'icon': '🏆',
                'requirement_type': 'longest_streak',
                'requirement_value': 30,
                'xp_reward': 300,
                'category': 'STREAK',
            },
            
            # Logros sociales
            {
                'code': 'first_review',
                'name': 'Crítico Novato',
                'description': 'Deja tu primera reseña de clase',
                'icon': '✍️',
                'requirement_type': 'total_reviews',
                'requirement_value': 1,
                'xp_reward': 10,
                'category': 'REVIEWS',
            },
            {
                'code': 'reviews_10',
                'name': 'Opinador Experto',
                'description': 'Has dejado 10 reseñas de clases',
                'icon': '⭐',
                'requirement_type': 'total_reviews',
                'requirement_value': 10,
                'xp_reward': 100,
                'category': 'REVIEWS',
            },
            {
                'code': 'first_referral',
                'name': 'Embajador',
                'description': 'Refiere a tu primer amigo al gimnasio',
                'icon': '🤝',
                'requirement_type': 'total_referrals',
                'requirement_value': 1,
                'xp_reward': 50,
                'category': 'SOCIAL',
            },
            {
                'code': 'referrals_5',
                'name': 'Influencer del Fitness',
                'description': 'Has referido a 5 personas',
                'icon': '📣',
                'requirement_type': 'total_referrals',
                'requirement_value': 5,
                'xp_reward': 300,
                'category': 'SOCIAL',
            },
            
            # Logros de nivel
            {
                'code': 'level_5',
                'name': 'Aprendiz Certificado',
                'description': 'Alcanzaste el nivel 5',
                'icon': '🥉',
                'requirement_type': 'current_level',
                'requirement_value': 5,
                'xp_reward': 100,
                'category': 'SPECIAL',
            },
            {
                'code': 'level_10',
                'name': 'Experto Reconocido',
                'description': 'Alcanzaste el nivel 10',
                'icon': '🥈',
                'requirement_type': 'current_level',
                'requirement_value': 10,
                'xp_reward': 200,
                'category': 'SPECIAL',
            },
            {
                'code': 'level_20',
                'name': 'Maestro del Gimnasio',
                'description': 'Alcanzaste el nivel 20',
                'icon': '🥇',
                'requirement_type': 'current_level',
                'requirement_value': 20,
                'xp_reward': 500,
                'category': 'SPECIAL',
            },
            {
                'code': 'level_30',
                'name': 'Leyenda Viviente',
                'description': 'Alcanzaste el nivel 30 - élite absoluta',
                'icon': '👑',
                'requirement_type': 'current_level',
                'requirement_value': 30,
                'xp_reward': 1000,
                'category': 'SPECIAL',
            },
            
            # Logros especiales
            {
                'code': 'early_bird',
                'name': 'Madrugador',
                'description': 'Asiste a una clase antes de las 7 AM',
                'icon': '🌅',
                'requirement_type': 'special',
                'requirement_value': 0,
                'xp_reward': 25,
                'category': 'SPECIAL',
            },
            {
                'code': 'night_owl',
                'name': 'Búho Nocturno',
                'description': 'Asiste a una clase después de las 9 PM',
                'icon': '🌙',
                'requirement_type': 'special',
                'requirement_value': 0,
                'xp_reward': 25,
                'category': 'SPECIAL',
            },
            {
                'code': 'weekend_warrior',
                'name': 'Guerrero de Fin de Semana',
                'description': 'Asiste a clases en sábado y domingo',
                'icon': '🏋️',
                'requirement_type': 'special',
                'requirement_value': 0,
                'xp_reward': 50,
                'category': 'SPECIAL',
            },
        ]

        total_created = 0
        total_updated = 0

        for gym in gyms:
            self.stdout.write(f'\n🏋️ Procesando gimnasio: {gym.name}')
            created_count = 0
            updated_count = 0

            for achievement_data in achievements:
                achievement, created = Achievement.objects.update_or_create(
                    gym=gym,
                    code=achievement_data['code'],
                    defaults={
                        'name': achievement_data['name'],
                        'description': achievement_data['description'],
                        'icon': achievement_data['icon'],
                        'requirement_type': achievement_data['requirement_type'],
                        'requirement_value': achievement_data['requirement_value'],
                        'xp_reward': achievement_data['xp_reward'],
                        'category': achievement_data['category'],
                        'is_active': True,
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            
            total_created += created_count
            total_updated += updated_count
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'   ✓ {created_count} creados, {updated_count} actualizados'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Proceso completado:\n'
                f'   • Total gimnasios: {gyms.count()}\n'
                f'   • Logros creados: {total_created}\n'
                f'   • Logros actualizados: {total_updated}\n'
                f'   • Total: {total_created + total_updated}'
            )
        )
