"""
Script to add demo client to some classes in the calendar
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from clients.models import Client
from activities.models import ActivitySession
from django.utils import timezone

def main():
    # Get demo client
    demo_client = Client.objects.filter(email='demo.cliente@mygym.com').first()
    
    if not demo_client:
        print("❌ Demo client not found")
        return
    
    print(f"✅ Found demo client: {demo_client.first_name} {demo_client.last_name}")
    
    # Get upcoming sessions (next week)
    now = timezone.now()
    upcoming_sessions = ActivitySession.objects.filter(
        gym=demo_client.gym,
        start_datetime__gte=now,
        status='SCHEDULED'
    ).order_by('start_datetime')[:5]
    
    if not upcoming_sessions:
        print("❌ No upcoming sessions found")
        return
    
    print(f"\n📅 Found {upcoming_sessions.count()} upcoming sessions")
    
    added_count = 0
    for session in upcoming_sessions:
        # Check if already in session
        if demo_client in session.attendees.all():
            print(f"⏭️  Already in: {session.activity.name} - {session.start_datetime.strftime('%d/%m %H:%M')}")
            continue
        
        # Check capacity
        if session.attendees.count() >= session.max_capacity:
            print(f"🚫 Full: {session.activity.name} - {session.start_datetime.strftime('%d/%m %H:%M')}")
            continue
        
        # Add to session
        session.attendees.add(demo_client)
        added_count += 1
        print(f"✅ Added to: {session.activity.name} - {session.start_datetime.strftime('%d/%m %H:%M')}")
    
    print(f"\n✨ Demo client added to {added_count} sessions")

if __name__ == '__main__':
    main()
