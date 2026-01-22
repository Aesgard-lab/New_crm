from django.template.loader import render_to_string
# from weasyprint import HTML  # Uncomment when installed
from django.conf import settings
import os

def generate_invoice_pdf(invoice):
    """
    Generates a PDF for the given invoice.
    """
    context = {'invoice': invoice, 'config': settings.BILLING_CONFIG}
    html_string = render_to_string('saas_billing/invoice_pdf.html', context)
    
    # Save to file
    filename = f"invoice_{invoice.invoice_number}.pdf"
    filepath = os.path.join(settings.MEDIA_ROOT, 'invoices', str(invoice.issue_date.year), str(invoice.issue_date.month), filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # HTML(string=html_string).write_pdf(filepath)
    
    # Return relative path for FileField
    return f"invoices/{invoice.issue_date.year}/{invoice.issue_date.month}/{filename}"
