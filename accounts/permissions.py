from django.apps import apps

def user_has_gym_permission(user, gym_id: int, perm_code: str) -> bool:
    """
    Comprueba si el usuario tiene permiso sobre un gym.
    - ADMIN: siempre True
    - STAFF: permiso explícito
    """
    if user.is_superuser:
        return True

    GymMembership = apps.get_model("accounts", "GymMembership")
    FranchiseMembership = apps.get_model("accounts", "FranchiseMembership")
    Gym = apps.get_model("organizations", "Gym")

    # 1. Comprobar si es Owner de la Franquicia a la que pertenece el Gym
    # Optimización: Podríamos pasar el objeto gym para ahorrar consulta, pero por id:
    gym = Gym.objects.filter(id=gym_id).values("franchise_id").first()
    if gym:
        is_franchise_owner = FranchiseMembership.objects.filter(
            user=user,
            franchise_id=gym["franchise_id"],
            role="OWNER" # Usar la constante de modelo idealmente
        ).exists()
        if is_franchise_owner:
            return True

    # 2. Comprobar membresía directa al Gym
    membership = GymMembership.objects.filter(
        user=user,
        gym_id=gym_id,
        is_active=True
    ).first()

    if not membership:
        return False

    if membership.role == "ADMIN":
        return True

    return membership.permissions.filter(code=perm_code).exists()
