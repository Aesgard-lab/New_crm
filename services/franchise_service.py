from django.db import transaction
from django.core.files.base import ContentFile
from django.db import transaction
from django.core.files.base import ContentFile
from activities.models import Activity, ActivityCategory, ActivityPolicy
from products.models import Product, ProductCategory
from services.models import Service, ServiceCategory
from memberships.models import MembershipPlan, PlanAccessRule
from finance.models import TaxRate
from clients.models import DocumentTemplate

class FranchisePropagationService:
    @staticmethod
    def propagate_tax_rate(source_tax, target_gyms):
        """
        Copies or updates a tax rate to the target gyms.
        """
        results = {'created': 0, 'updated': 0, 'errors': []}

        for gym in target_gyms:
            if gym == source_tax.gym:
                continue

            try:
                with transaction.atomic():
                    target_tax, created = TaxRate.objects.update_or_create(
                        gym=gym,
                        name=source_tax.name,
                        defaults={
                            'rate_percent': source_tax.rate_percent,
                            'is_active': source_tax.is_active,
                        }
                    )

                    if created:
                        results['created'] += 1
                    else:
                        results['updated'] += 1
                        
            except Exception as e:
                results['errors'].append(f"Error propagando a {gym.name}: {str(e)}")
        
        return results

    @staticmethod
    def propagate_activity(source_activity, target_gyms):
        """
        Copies or updates an activity to the target gyms.
        Handles dependency resolution (Category, Policy).
        """
        results = {'created': 0, 'updated': 0, 'errors': []}

        for gym in target_gyms:
            if gym == source_activity.gym:
                continue

            try:
                with transaction.atomic():
                    # 1. Resolve Dependencies
                    category = FranchisePropagationService._get_or_create_category(source_activity.category, gym)
                    policy = FranchisePropagationService._get_or_create_policy(source_activity.policy, gym)
                    
                    # 2. Find or Create Activity
                    target_activity, created = Activity.objects.update_or_create(
                        gym=gym,
                        name=source_activity.name,
                        defaults={
                            'description': source_activity.description,
                            'category': category,
                            'policy': policy,
                            'color': source_activity.color,
                            'duration': source_activity.duration,
                            'base_capacity': source_activity.base_capacity,
                            'intensity_level': source_activity.intensity_level,
                            'video_url': source_activity.video_url,
                        }
                    )
                    
                    # 3. Handle Image (only if changed or new)
                    # This is basic; for production, maybe check checksums or just overwrite if created
                    if source_activity.image and (created or not target_activity.image):
                        # Simple file copy
                        target_activity.image.save(
                            source_activity.image.name,
                            source_activity.image.file,
                            save=False
                        )
                        target_activity.save()

                    if created:
                        results['created'] += 1
                    else:
                        results['updated'] += 1
                        
            except Exception as e:
                results['errors'].append(f"Error propagating to {gym.name}: {str(e)}")
        
        return results

    @staticmethod
    def propagate_product(source_product, target_gyms):
        results = {'created': 0, 'updated': 0, 'errors': []}

        for gym in target_gyms:
            if gym == source_product.gym:
                continue

            try:
                with transaction.atomic():
                    category = FranchisePropagationService._get_or_create_product_category(source_product.category, gym)
                    tax_rate = FranchisePropagationService._get_or_create_tax_rate(source_product.tax_rate, gym)
                    
                    target_product, created = Product.objects.update_or_create(
                        gym=gym,
                        name=source_product.name,
                        defaults={
                            'category': category,
                            'description': source_product.description,
                            'price_strategy': source_product.price_strategy,
                            'tax_rate': tax_rate,
                            'barcode': source_product.barcode,  # Código de barras del fabricante (compartido)
                            'barcode_type': source_product.barcode_type,
                            # SKU se genera automáticamente por gym, no se copia
                            'cost_price': source_product.cost_price,
                            'base_price': source_product.base_price,
                            'supplier_name': source_product.supplier_name,
                            'supplier_reference': source_product.supplier_reference,
                            'is_visible_online': source_product.is_visible_online,
                            # Note: Stock is NOT copied as it is local physics
                        }
                    )
                    
                    if source_product.image and (created or not target_product.image):
                        target_product.image.save(source_product.image.name, source_product.image.file, save=False)
                        target_product.save()

                    if created: results['created'] += 1
                    else: results['updated'] += 1
            except Exception as e:
                results['errors'].append(f"Error propagating Product to {gym.name}: {str(e)}")
        return results

    @staticmethod
    def propagate_service(source_service, target_gyms):
        results = {'created': 0, 'updated': 0, 'errors': []}

        for gym in target_gyms:
            if gym == source_service.gym: continue
            try:
                with transaction.atomic():
                    category = FranchisePropagationService._get_or_create_service_category(source_service.category, gym)
                    tax_rate = FranchisePropagationService._get_or_create_tax_rate(source_service.tax_rate, gym)
                    # Note: Room is NOT copied as it is physical space. default_room will be None.

                    target_service, created = Service.objects.update_or_create(
                        gym=gym,
                        name=source_service.name,
                        defaults={
                            'category': category,
                            'description': source_service.description,
                            'color': source_service.color,
                            'duration': source_service.duration,
                            'max_attendees': source_service.max_attendees,
                            'base_price': source_service.base_price,
                            'tax_rate': tax_rate,
                            'price_strategy': source_service.price_strategy,
                            'is_visible_online': source_service.is_visible_online,
                        }
                    )
                    
                    if source_service.image and (created or not target_service.image):
                        target_service.image.save(source_service.image.name, source_service.image.file, save=False)
                        target_service.save()

                    if created: results['created'] += 1
                    else: results['updated'] += 1
            except Exception as e:
                results['errors'].append(f"Error propagating Service to {gym.name}: {str(e)}")
        return results

    @staticmethod
    def propagate_membership(source_plan, target_gyms):
        results = {'created': 0, 'updated': 0, 'errors': []}

        for gym in target_gyms:
            if gym == source_plan.gym: continue
            try:
                with transaction.atomic():
                    tax_rate = FranchisePropagationService._get_or_create_tax_rate(source_plan.tax_rate, gym)
                    
                    target_plan, created = MembershipPlan.objects.update_or_create(
                        gym=gym,
                        name=source_plan.name,
                        defaults={
                            'description': source_plan.description,
                            'base_price': source_plan.base_price,
                            'tax_rate': tax_rate,
                            'price_strategy': source_plan.price_strategy,
                            'is_recurring': source_plan.is_recurring,
                            'frequency_amount': source_plan.frequency_amount,
                            'frequency_unit': source_plan.frequency_unit,
                            'pack_validity_days': source_plan.pack_validity_days,
                            'prorate_first_month': source_plan.prorate_first_month,
                            'is_visible_online': source_plan.is_visible_online,
                            'contract_required': source_plan.contract_required,
                            'contract_content': source_plan.contract_content
                        }
                    )
                    
                    if source_plan.image and (created or not target_plan.image):
                        target_plan.image.save(source_plan.image.name, source_plan.image.file, save=False)
                        target_plan.save()

                    # Propagate Access Rules
                    # We wipe existing rules and re-create to ensure sync
                    target_plan.access_rules.all().delete()
                    for rule in source_plan.access_rules.all():
                        new_rule = PlanAccessRule(plan=target_plan, quantity=rule.quantity, period=rule.period)
                        
                        # Try to link dependencies IF they exist by name
                        if rule.activity_category:
                            new_rule.activity_category = FranchisePropagationService._get_or_create_category(rule.activity_category, gym)
                        if rule.service_category:
                            new_rule.service_category = FranchisePropagationService._get_or_create_service_category(rule.service_category, gym)
                            
                        if rule.activity:
                            new_rule.activity = Activity.objects.filter(gym=gym, name=rule.activity.name).first()
                        if rule.service:
                            new_rule.service = Service.objects.filter(gym=gym, name=rule.service.name).first()
                            
                        new_rule.save()

                    if created: results['created'] += 1
                    else: results['updated'] += 1
            except Exception as e:
                results['errors'].append(f"Error propagating Membership to {gym.name}: {str(e)}")
        return results

    @staticmethod
    def _get_or_create_category(source_category, target_gym):
        if not source_category:
            return None
            
        # Try to find by name
        category, created = ActivityCategory.objects.get_or_create(
            gym=target_gym,
            name=source_category.name,
            defaults={
                'icon': source_category.icon # Note: File copy not implemented for simplicity here yet
            }
        )
        return category

    @staticmethod
    def _get_or_create_policy(source_policy, target_gym):
        if not source_policy:
            return None

        # Try to find by name
        policy, created = ActivityPolicy.objects.get_or_create(
            gym=target_gym,
            name=source_policy.name,
            defaults={
                'booking_window_mode': source_policy.booking_window_mode,
                'booking_window_value': source_policy.booking_window_value,
                'booking_time_release': source_policy.booking_time_release,
                'waitlist_enabled': source_policy.waitlist_enabled,
                'waitlist_mode': source_policy.waitlist_mode,
                'waitlist_limit': source_policy.waitlist_limit,
                'auto_promote_cutoff_hours': source_policy.auto_promote_cutoff_hours,
                'cancellation_window_hours': source_policy.cancellation_window_hours,
                'penalty_type': source_policy.penalty_type,
                'fee_amount': source_policy.fee_amount,
            }
        )
        # If it existed, we MIGHT want to update it to match the source?
        # For now, we assume "Same Name = Same Policy" and don't overwrite local changes unless requested.
        # But for propagation, usually "Master" overrides. Let's update it.
        if not created:
            policy.booking_window_mode = source_policy.booking_window_mode
            policy.booking_window_value = source_policy.booking_window_value
            # ... (Update all fields to ensure sync)
            policy.save()
            
        return policy
    
    @staticmethod
    def _get_or_create_product_category(source_category, target_gym):
        if not source_category: return None
        # Naive parent handling: we ignore parent for now to avoid recursion hell, or simple check
        cat, _ = ProductCategory.objects.get_or_create(gym=target_gym, name=source_category.name)
        return cat

    @staticmethod
    def _get_or_create_service_category(source_category, target_gym):
        if not source_category: return None
        cat, _ = ServiceCategory.objects.get_or_create(gym=target_gym, name=source_category.name)
        return cat

    @staticmethod
    def _get_or_create_tax_rate(source_tax, target_gym):
        if not source_tax: return None
        # Tax rates are tricky, assumed same name = same tax
        tax, _ = TaxRate.objects.get_or_create(
            gym=target_gym, 
            name=source_tax.name,
            defaults={'rate_percent': source_tax.rate_percent}
        )
        return tax

    @staticmethod
    def propagate_document_template(source_template, target_gyms, user=None):
        """
        Copies or updates a document template to the target gyms.
        """
        results = {'created': 0, 'updated': 0, 'errors': []}

        for gym in target_gyms:
            if gym == source_template.gym:
                continue

            try:
                with transaction.atomic():
                    target_template, created = DocumentTemplate.objects.update_or_create(
                        gym=gym,
                        name=source_template.name,
                        defaults={
                            'document_type': source_template.document_type,
                            'content': source_template.content,
                            'requires_signature': source_template.requires_signature,
                            'is_active': source_template.is_active,
                            'created_by': user,
                        }
                    )

                    if created:
                        results['created'] += 1
                    else:
                        results['updated'] += 1
                        
            except Exception as e:
                results['errors'].append(f"Error propagando a {gym.name}: {str(e)}")
        
        return results
