import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sales_logbook.settings')
django.setup()

from core.models import Category, Product

def repopulate():
    # Set encoding for Windows console
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # Clear existing
    print("Clearing existing products and categories...")
    Product.objects.all().delete()
    Category.objects.all().delete()

    data = {
        "👕 Clothing / Apparel": [
            ("Oversized T-shirt", 150),
            ("Croptop", 120),
            ("Polo Shirt", 180),
            ("Hoodie", 250),
            ("Denim Shorts", 180),
            ("Jogging Pants", 200),
            ("Dress (Preloved)", 220),
            ("Branded Shirt (Preloved)", 200),
            ("Jacket", 300),
            ("Sando", 100),
        ],
        "📱 Phone Accessories": [
            ("Phone Case", 100),
            ("Charger Cable", 80),
            ("Fast Charger Adapter", 150),
            ("Power Bank (10,000mAh)", 350),
            ("Wireless Earbuds", 500),
            ("Wired Earphones", 120),
            ("Ring Light (Small)", 250),
            ("Phone Holder/Stand", 120),
            ("Screen Protector", 50),
            ("Bluetooth Speaker", 400),
        ],
        "💄 Beauty Products": [
            ("Lip Tint", 120),
            ("Lipstick", 150),
            ("Facial Cleanser", 150),
            ("Toner", 180),
            ("Sunscreen", 200),
            ("Skincare Set", 350),
            ("Whitening Soap", 80),
            ("Lotion", 180),
            ("Face Mask (per pack)", 100),
            ("Beauty Bundle Set", 500),
        ],
        "🏠 Home & Essentials": [
            ("Storage Box", 200),
            ("Mini Fan (Rechargeable)", 180),
            ("LED Strip Lights", 150),
            ("Extension Cord", 220),
            ("Kitchen Utensils Set", 220),
            ("Water Bottle", 100),
            ("Tumbler", 180),
            ("Electric Kettle", 450),
            ("Rice Cooker (Small)", 900),
            ("Table Organizer", 150),
        ],
        "🎒 School & Office Supplies": [
            ("Notebook", 50),
            ("Ballpen (per piece)", 10),
            ("Gel Pen Set", 60),
            ("Highlighter Set", 80),
            ("Planner", 150),
            ("Pencil Case", 100),
            ("Backpack", 400),
            ("Folder", 30),
            ("Bond Paper (ream)", 250),
            ("Calculator", 180),
        ],
        "🐶 Pet Supplies": [
            ("Dog Food (1kg repack)", 180),
            ("Cat Food (1kg repack)", 160),
            ("Dog Treats", 120),
            ("Cat Treats", 100),
            ("Pet Bowl", 100),
            ("Pet Clothes", 150),
            ("Dog Leash", 120),
            ("Cat Litter (5L)", 200),
            ("Pet Shampoo", 180),
            ("Cat Toy", 80),
        ]
    }

    for cat_name, products in data.items():
        category = Category.objects.create(name=cat_name)
        print(f"Created Category: {cat_name}")
        for p_name, p_price in products:
            Product.objects.create(
                name=p_name,
                category=category,
                price=p_price,
                stock=50, # Default stock
                is_active=True
            )
            print(f"  - Created Product: {p_name} (₱{p_price})")

    print("\nRepopulation complete!")

if __name__ == "__main__":
    repopulate()
