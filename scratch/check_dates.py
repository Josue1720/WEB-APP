import os
import sys
import django
from django.utils import timezone

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_logbook.settings')
django.setup()

from core.models import Sale

print(f"Current UTC time: {timezone.now()}")
print(f"Current Manila time: {timezone.localtime(timezone.now())}")

last_sales = Sale.objects.order_by('-date')[:5]
print("\nLast 5 Sales:")
for s in last_sales:
    print(f"ID: {s.id}, Date (UTC): {s.date}, Date (Manila): {timezone.localtime(s.date)}, Total: {s.total_amount}")
