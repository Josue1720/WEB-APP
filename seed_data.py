"""
Seed script to create initial admin user and sample data.
Run with: python manage.py shell < seed_data.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_logbook.settings')

# Setup Django if not already
try:
    django.setup()
except:
    pass

from core.models import User, Product, Sale, SaleItem
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

# ─── Create Users ───
print("Creating users...")

admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'first_name': 'System',
        'last_name': 'Admin',
        'email': 'admin@saleslogbook.com',
        'role': 'admin',
        'is_staff': True,
        'is_superuser': True,
    }
)
if created:
    admin_user.set_password('admin123')
    admin_user.save()
    print("  ✓ Admin user created (username: admin, password: admin123)")
else:
    print("  - Admin user already exists")

manager_user, created = User.objects.get_or_create(
    username='manager',
    defaults={
        'first_name': 'Juan',
        'last_name': 'Dela Cruz',
        'email': 'manager@saleslogbook.com',
        'role': 'manager',
    }
)
if created:
    manager_user.set_password('manager123')
    manager_user.save()
    print("  ✓ Manager user created (username: manager, password: manager123)")
else:
    print("  - Manager user already exists")

staff_user, created = User.objects.get_or_create(
    username='staff',
    defaults={
        'first_name': 'Maria',
        'last_name': 'Santos',
        'email': 'staff@saleslogbook.com',
        'role': 'staff',
    }
)
if created:
    staff_user.set_password('staff123')
    staff_user.save()
    print("  ✓ Staff user created (username: staff, password: staff123)")
else:
    print("  - Staff user already exists")

# ─── Create Products ───
print("\nCreating products...")

products_data = [
    {'name': 'Paracetamol 500mg', 'price': Decimal('5.50'), 'stock': 200, 'sku': 'MED-001'},
    {'name': 'Amoxicillin 500mg', 'price': Decimal('12.00'), 'stock': 150, 'sku': 'MED-002'},
    {'name': 'Biogesic Tablet', 'price': Decimal('6.75'), 'stock': 300, 'sku': 'MED-003'},
    {'name': 'Neozep Forte', 'price': Decimal('8.50'), 'stock': 180, 'sku': 'MED-004'},
    {'name': 'Bioflu Tablet', 'price': Decimal('15.00'), 'stock': 120, 'sku': 'MED-005'},
    {'name': 'Ibuprofen 200mg', 'price': Decimal('7.25'), 'stock': 250, 'sku': 'MED-006'},
    {'name': 'Cetirizine 10mg', 'price': Decimal('4.50'), 'stock': 200, 'sku': 'MED-007'},
    {'name': 'Loperamide 2mg', 'price': Decimal('6.00'), 'stock': 100, 'sku': 'MED-008'},
    {'name': 'Antacid Tablet', 'price': Decimal('3.50'), 'stock': 300, 'sku': 'MED-009'},
    {'name': 'Vitamin C 500mg', 'price': Decimal('8.00'), 'stock': 400, 'sku': 'VIT-001'},
    {'name': 'Multivitamins', 'price': Decimal('12.50'), 'stock': 200, 'sku': 'VIT-002'},
    {'name': 'Face Mask (Box)', 'price': Decimal('150.00'), 'stock': 50, 'sku': 'SUP-001'},
    {'name': 'Alcohol 500ml', 'price': Decimal('85.00'), 'stock': 80, 'sku': 'SUP-002'},
    {'name': 'Cotton Balls (Pack)', 'price': Decimal('35.00'), 'stock': 60, 'sku': 'SUP-003'},
    {'name': 'Band-Aid (Box)', 'price': Decimal('45.00'), 'stock': 75, 'sku': 'SUP-004'},
]

created_products = []
for pd in products_data:
    product, created = Product.objects.get_or_create(
        sku=pd['sku'],
        defaults=pd
    )
    created_products.append(product)
    if created:
        print(f"  ✓ Product created: {product.name}")
    else:
        print(f"  - Product exists: {product.name}")

# ─── Create Sample Sales ───
print("\nCreating sample sales...")

if Sale.objects.count() == 0:
    now = timezone.now()
    customers = ['Walk-in', 'Juan Tamad', 'Maria Clara', 'Jose Rizal', 'Andres Bonifacio', None, None]
    staff_users = [admin_user, manager_user, staff_user]

    for day_offset in range(14, -1, -1):
        sale_date = now - timedelta(days=day_offset)
        num_sales = random.randint(2, 6)

        for _ in range(num_sales):
            sale = Sale(
                user=random.choice(staff_users),
                customer_name=random.choice(customers),
                date=sale_date.replace(
                    hour=random.randint(8, 17),
                    minute=random.randint(0, 59)
                ),
            )
            sale.save()

            # Add 1-4 items per sale
            num_items = random.randint(1, 4)
            selected_products = random.sample(created_products, min(num_items, len(created_products)))

            for product in selected_products:
                qty = random.randint(1, 5)
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    product_name=product.name,
                    quantity=qty,
                    price=product.price,
                )

            sale.recalculate_total()

    print(f"  ✓ Created {Sale.objects.count()} sample sales with {SaleItem.objects.count()} line items")
else:
    print("  - Sample sales already exist")

print("\n✅ Seed data complete!")
print("─" * 40)
print("Login credentials:")
print("  Admin:   admin / admin123")
print("  Manager: manager / manager123")
print("  Staff:   staff / staff123")
print("─" * 40)
