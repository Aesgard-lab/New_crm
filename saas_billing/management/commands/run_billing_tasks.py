"""
Management command to run daily SaaS billing tasks.

Usage:
    python manage.py run_billing_tasks
    python manage.py run_billing_tasks --task=overdue
    python manage.py run_billing_tasks --task=reminders
    python manage.py run_billing_tasks --task=invoices
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from saas_billing.tasks import task_service


class Command(BaseCommand):
    help = 'Run SaaS billing maintenance tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            choices=['all', 'overdue', 'reminders', 'invoices', 'mrr'],
            default='all',
            help='Which task to run (default: all)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
    
    def handle(self, *args, **options):
        task = options['task']
        dry_run = options['dry_run']
        
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(f"SaaS Billing Tasks - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"{'='*50}\n")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made\n"))
            self._show_status()
            return
        
        if task == 'all':
            self._run_all_tasks()
        elif task == 'overdue':
            self._run_overdue()
        elif task == 'reminders':
            self._run_reminders()
        elif task == 'invoices':
            self._run_invoices()
        elif task == 'mrr':
            self._run_mrr()
    
    def _show_status(self):
        """Show current status without making changes."""
        from datetime import date
        from saas_billing.models import GymSubscription, Invoice
        
        today = date.today()
        
        # Active subscriptions
        active = GymSubscription.objects.filter(status='ACTIVE').count()
        past_due = GymSubscription.objects.filter(status='PAST_DUE').count()
        suspended = GymSubscription.objects.filter(status='SUSPENDED').count()
        
        # Overdue
        overdue = GymSubscription.objects.filter(
            status='ACTIVE',
            current_period_end__lt=today
        ).count()
        
        # Pending invoices
        pending_invoices = Invoice.objects.filter(status='PENDING').count()
        failed_invoices = Invoice.objects.filter(status='FAILED').count()
        
        self.stdout.write("\nCurrent Status:")
        self.stdout.write(f"  Active subscriptions: {active}")
        self.stdout.write(f"  Past due: {past_due}")
        self.stdout.write(f"  Suspended: {suspended}")
        self.stdout.write(f"  Would be marked overdue: {overdue}")
        self.stdout.write(f"  Pending invoices: {pending_invoices}")
        self.stdout.write(f"  Failed invoices: {failed_invoices}")
    
    def _run_all_tasks(self):
        """Run all daily tasks."""
        self.stdout.write("Running ALL daily tasks...\n")
        
        results = task_service.run_daily_tasks()
        
        self.stdout.write(self.style.SUCCESS("\n✅ All tasks completed!"))
        self._print_results(results)
    
    def _run_overdue(self):
        """Run overdue processing only."""
        self.stdout.write("Processing overdue subscriptions...\n")
        
        results = task_service.process_overdue_subscriptions()
        
        self.stdout.write(self.style.SUCCESS("\n✅ Overdue processing completed!"))
        self.stdout.write(f"  Checked: {results['checked']}")
        self.stdout.write(f"  Marked past due: {results['marked_past_due']}")
        self.stdout.write(f"  Suspended: {results['suspended']}")
        self.stdout.write(f"  Alerts sent: {results['alerts_sent']}")
    
    def _run_reminders(self):
        """Run reminder emails only."""
        self.stdout.write("Sending payment reminders...\n")
        
        results = task_service.send_payment_reminders()
        
        self.stdout.write(self.style.SUCCESS("\n✅ Reminders sent!"))
        self.stdout.write(f"  Upcoming reminders: {results['upcoming_reminders']}")
        self.stdout.write(f"  Overdue reminders: {results['overdue_reminders']}")
    
    def _run_invoices(self):
        """Run invoice generation only."""
        self.stdout.write("Generating pending invoices...\n")
        
        results = task_service.generate_pending_invoices()
        
        self.stdout.write(self.style.SUCCESS("\n✅ Invoice generation completed!"))
        self.stdout.write(f"  Invoices created: {results['invoices_created']}")
        self.stdout.write(f"  Total amount: {results['total_amount']:.2f}€")
    
    def _run_mrr(self):
        """Calculate and report MRR."""
        self.stdout.write("Calculating MRR metrics...\n")
        
        results = task_service.calculate_and_store_mrr()
        
        self.stdout.write(self.style.SUCCESS("\n✅ MRR calculated!"))
        self.stdout.write(f"  Current MRR: {results['current_mrr']:.2f}€")
        self.stdout.write(f"  Previous MRR: {results['previous_mrr']:.2f}€")
        self.stdout.write(f"  Change: {results['change']:.2f}€ ({results['change_percent']:.1f}%)")
    
    def _print_results(self, results):
        """Pretty print task results."""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("SUMMARY")
        self.stdout.write("="*50)
        
        if 'overdue' in results:
            o = results['overdue']
            self.stdout.write(f"\nOverdue Processing:")
            self.stdout.write(f"  - Marked past due: {o['marked_past_due']}")
            self.stdout.write(f"  - Suspended: {o['suspended']}")
        
        if 'reminders' in results:
            r = results['reminders']
            self.stdout.write(f"\nReminders Sent:")
            self.stdout.write(f"  - Upcoming: {r['upcoming_reminders']}")
            self.stdout.write(f"  - Overdue: {r['overdue_reminders']}")
        
        if 'invoices' in results:
            i = results['invoices']
            self.stdout.write(f"\nInvoices Generated:")
            self.stdout.write(f"  - Count: {i['invoices_created']}")
            self.stdout.write(f"  - Total: {i['total_amount']:.2f}€")
        
        if 'mrr' in results:
            m = results['mrr']
            self.stdout.write(f"\nMRR Metrics:")
            self.stdout.write(f"  - Current: {m['current_mrr']:.2f}€")
            self.stdout.write(f"  - Change: {m['change']:.2f}€")
