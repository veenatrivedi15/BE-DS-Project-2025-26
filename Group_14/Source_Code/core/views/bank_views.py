from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import TemplateView
from django.http import HttpResponse
import csv
import json
from io import StringIO
from datetime import datetime, timedelta

def is_bank_admin(user):
    return user.is_authenticated and user.is_bank_admin

@login_required
@user_passes_test(is_bank_admin)
def bank_dashboard(request):
    """
    Bank admin dashboard
    """
    context = {
        'title': 'Bank Dashboard',
        'active_page': 'dashboard'
    }
    return render(request, 'bank/dashboard.html', context)

@login_required
@user_passes_test(is_bank_admin)
def bank_trading(request):
    """
    Bank trading platform
    """
    context = {
        'title': 'Trading Platform',
        'active_page': 'trading'
    }
    return render(request, 'bank/trading.html', context)

class BankReportsView(TemplateView):
    template_name = 'bank/reports.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reports'
        context['active_page'] = 'reports'
        return context

@login_required
@user_passes_test(is_bank_admin)
def export_report(request, report_type, date_range, format_type):
    """
    Export report data in CSV or PDF format
    """
    # Placeholder for report generation logic
    if format_type == 'csv':
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{date_range}.csv"'
        
        # Create CSV writer
        csv_file = StringIO()
        writer = csv.writer(csv_file)
        
        # Write header row
        if report_type == 'summary':
            writer.writerow(['Date', 'Total Transactions', 'Volume', 'Value'])
        elif report_type == 'transactions':
            writer.writerow(['ID', 'Date', 'Seller', 'Buyer', 'Credits', 'Price', 'Status'])
        elif report_type == 'price':
            writer.writerow(['Date', 'Average Price', 'Min Price', 'Max Price'])
        elif report_type == 'employer':
            writer.writerow(['Employer', 'Credits Bought', 'Credits Sold', 'Net Position', 'Total Value'])
        
        # Write placeholder data
        writer.writerow(['2023-01-01', '10', '100', '$1000'])
        writer.writerow(['2023-01-02', '15', '150', '$1500'])
        
        response.write(csv_file.getvalue())
        return response
    
    elif format_type == 'pdf':
        # PDF generation would go here
        # For now, return a simple text response
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{date_range}.txt"'
        response.write(f"Sample {report_type} report for {date_range}")
        return response 