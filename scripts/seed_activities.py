from activities.models import ActivityCategory, CancellationPolicy
from organizations.models import Gym

def seed_data():
    gym = Gym.objects.first()
    if not gym:
        print("No gym found")
        return

    # Create Categories
    categories = ['Fuerza', 'Cardio', 'Yoga / Pilates', 'Funcional']
    for cat_name in categories:
        ActivityCategory.objects.get_or_create(gym=gym, name=cat_name)
    print(f"Created {len(categories)} categories")

    # Create Policies
    CancellationPolicy.objects.get_or_create(
        gym=gym, 
        name="Estándar (12h)", 
        defaults={'window_hours': 12, 'penalty_type': 'FORFEIT'}
    )
    CancellationPolicy.objects.get_or_create(
        gym=gym, 
        name="Estricta (24h)", 
        defaults={'window_hours': 24, 'penalty_type': 'STRIKE'}
    )
    print("Created policies")

if __name__ == '__main__':
    seed_data()
