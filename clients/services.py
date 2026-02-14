from django.db.models import Q, Max, Count
from django.utils import timezone
from datetime import timedelta

class ClientFilterService:
    @staticmethod
    def filter_clients(queryset, params):
        """
        Applies filters to the Client queryset based on request parameters.
        params: dict-like object (request.GET)
        """
        clients = queryset

        # 1. Text Search
        query = params.get("q", "").strip()
        if query:
            clients = clients.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone_number__icontains=query)
            )

        # 2. Status Filter
        statuses = params.getlist("status")
        if statuses and 'all' not in statuses:
            normal_statuses = [s for s in statuses if s != 'UNPAID']
            has_unpaid_filter = 'UNPAID' in statuses
            
            if normal_statuses and has_unpaid_filter:
                clients = clients.filter(
                    Q(status__in=normal_statuses) | 
                    Q(memberships__status='PENDING_PAYMENT')
                ).distinct()
            elif has_unpaid_filter:
                clients = clients.filter(memberships__status='PENDING_PAYMENT').distinct()
            elif normal_statuses:
                clients = clients.filter(status__in=normal_statuses)
        
        # Legacy Status Support
        status = params.get("status_single", "all")
        if status and status != "all" and not statuses:
            clients = clients.filter(status=status)

        # 3. Tags
        selected_tags = params.getlist("tags")
        if selected_tags:
            clients = clients.filter(tags__id__in=selected_tags)

        # 4. Client Type (Company/Individual)
        companies = params.getlist("company")
        if companies and 'all' not in companies:
            company_q = Q()
            if 'company' in companies:
                company_q |= Q(is_company_client=True)
            if 'individual' in companies:
                company_q |= Q(is_company_client=False)
            clients = clients.filter(company_q)

        # 5. Payment Gateway
        gateways = params.getlist("gateway")
        if gateways and 'all' not in gateways:
            gateway_q = Q()
            if 'stripe' in gateways:
                gateway_q |= Q(preferred_gateway='STRIPE') | Q(stripe_customer_id__isnull=False)
            if 'redsys' in gateways:
                gateway_q |= Q(preferred_gateway='REDSYS') | Q(redsys_tokens__isnull=False)
            if 'auto' in gateways:
                gateway_q |= Q(preferred_gateway='AUTO', stripe_customer_id__isnull=True)
            clients = clients.filter(gateway_q).distinct()
        
        # Legacy Gateway Support
        gateway = params.get("gateway_single", "all")
        if gateway and gateway != "all" and not gateways:
            if gateway == "stripe":
                clients = clients.filter(Q(preferred_gateway='STRIPE') | Q(stripe_customer_id__isnull=False))
            elif gateway == "redsys":
                clients = clients.filter(Q(preferred_gateway='REDSYS') | Q(redsys_tokens__isnull=False)).distinct()
            elif gateway == "auto":
                clients = clients.filter(preferred_gateway='AUTO', stripe_customer_id__isnull=True).exclude(redsys_tokens__isnull=False)

        # 6. Gender
        genders = params.getlist("gender")
        if genders and 'all' not in genders:
            clients = clients.filter(gender__in=genders)
        
        # Legacy Gender Support
        gender = params.get("gender_single", "all")
        if gender and gender != "all" and not genders:
            clients = clients.filter(gender=gender)

        # 7. Wallet Balance
        wallet_balance = params.getlist("wallet_balance")
        if wallet_balance and 'all' not in wallet_balance:
            wallet_q = Q()
            if 'positive' in wallet_balance:
                wallet_q |= Q(wallet__balance__gt=0)
            if 'negative' in wallet_balance:
                wallet_q |= Q(wallet__balance__lt=0)
            if 'zero' in wallet_balance:
                wallet_q |= Q(wallet__balance=0)
            if 'no_wallet' in wallet_balance:
                wallet_q |= Q(wallet__isnull=True)
            clients = clients.filter(wallet_q)

        # 8. Membership Plans
        membership_plans_filter = params.getlist("membership_plan")
        if membership_plans_filter and 'all' not in membership_plans_filter:
            clients = clients.filter(memberships__plan_id__in=membership_plans_filter).distinct()

        # 9. Services & Products
        services_filter = params.getlist("service")
        if services_filter and 'all' not in services_filter:
            clients = clients.filter(
                Q(session_bookings__session__service_id__in=services_filter) |
                Q(memberships__plan__services__id__in=services_filter)
            ).distinct()
        
        products_filter = params.getlist("product")
        if products_filter and 'all' not in products_filter:
            clients = clients.filter(orders__items__product_id__in=products_filter).distinct()

        # 10. Origin
        created_froms = params.getlist("created_from")
        if created_froms and 'all' not in created_froms:
            clients = clients.filter(created_from__in=created_froms)

        # 11. Dates
        date_from = params.get('date_from', '')
        date_to = params.get('date_to', '')
        if date_from:
            clients = clients.filter(created_at__date__gte=date_from)
        if date_to:
            clients = clients.filter(created_at__date__lte=date_to)

        # 12. Engagement Filters
        days_no_visit = params.get('days_no_visit', '')
        if days_no_visit and days_no_visit.isdigit():
            days = int(days_no_visit)
            threshold_date = timezone.now().date() - timedelta(days=days)
            clients = clients.annotate(
                last_visit_date=Max('visits__date')
            ).filter(
                Q(last_visit_date__lt=threshold_date) | Q(last_visit_date__isnull=True)
            )

        days_no_booking = params.get('days_no_booking', '')
        if days_no_booking and days_no_booking.isdigit():
            days = int(days_no_booking)
            threshold_date = timezone.now().date() - timedelta(days=days)
            clients = clients.annotate(
                last_booking_date=Max('session_bookings__created_at')
            ).filter(
                Q(last_booking_date__date__lt=threshold_date) | Q(last_booking_date__isnull=True)
            )

        membership_expires_days = params.get('membership_expires_days', '')
        if membership_expires_days and membership_expires_days.isdigit():
            days = int(membership_expires_days)
            threshold_date = timezone.now().date() + timedelta(days=days)
            clients = clients.filter(
                memberships__status='ACTIVE',
                memberships__end_date__lte=threshold_date,
                memberships__end_date__gte=timezone.now().date()
            ).distinct()

        # 13. Cancellation & Pauses
        cancelled_from = params.get('cancelled_from', '')
        cancelled_to = params.get('cancelled_to', '')
        if cancelled_from:
            clients = clients.filter(memberships__status='CANCELLED', memberships__updated_at__date__gte=cancelled_from).distinct()
        if cancelled_to:
            clients = clients.filter(memberships__status='CANCELLED', memberships__updated_at__date__lte=cancelled_to).distinct()

        has_active_pause = params.get('has_active_pause', '')
        if has_active_pause == 'yes':
            today = timezone.now().date()
            clients = clients.filter(
                memberships__pauses__status='ACTIVE',
                memberships__pauses__start_date__lte=today,
                memberships__pauses__end_date__gte=today
            ).distinct()
        elif has_active_pause == 'no':
            today = timezone.now().date()
            clients = clients.exclude(
                memberships__pauses__status='ACTIVE',
                memberships__pauses__start_date__lte=today,
                memberships__pauses__end_date__gte=today
            )

        # 14. No-Shows
        min_no_shows = params.get('min_no_shows', '')
        if min_no_shows and min_no_shows.isdigit():
            min_count = int(min_no_shows)
            clients = clients.annotate(
                noshow_count=Count('visits', filter=Q(visits__status='NOSHOW'))
            ).filter(noshow_count__gte=min_count)

        # 15. App Usage
        has_app_filter = params.getlist('has_app')
        if has_app_filter and 'all' not in has_app_filter:
            app_q = Q()
            if 'yes' in has_app_filter:
                app_q |= Q(app_access_count__gt=0)
            if 'no' in has_app_filter:
                app_q |= Q(app_access_count=0) | Q(app_access_count__isnull=True)
            clients = clients.filter(app_q)

        return clients
