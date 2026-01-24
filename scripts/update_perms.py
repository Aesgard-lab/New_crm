from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import Role, RolePermission
from activities.models import Activity, Room, ActivityCategory, CancellationPolicy
from services.models import Service
from finance.models import TaxRate

def update_owner_perms():
    owner_role = Role.objects.filter(name='Owner').first()
    if not owner_role:
        print("Owner role not found")
        return

    models = [Activity, Room, ActivityCategory, CancellationPolicy, Service, TaxRate]
    
    for model in models:
        content_type = ContentType.objects.get_for_model(model)
        perms = Permission.objects.filter(content_type=content_type)
        
        for perm in perms:
            RolePermission.objects.get_or_create(role=owner_role, permission=perm)
            print(f"Added {perm.codename} to Owner")

if __name__ == '__main__':
    update_owner_perms()
    print("Permissions updated.")
