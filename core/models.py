from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Custom user model with role-based access control."""
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Sales Staff'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin_user(self):
        return self.role == 'admin'

    @property
    def is_manager_user(self):
        return self.role == 'manager'

    @property
    def is_staff_user(self):
        return self.role == 'staff'


class Product(models.Model):
    """Product/service model for the sales catalog."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=0, help_text="Current stock quantity")
    sku = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name="SKU")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - ₱{self.price:,.2f}"


class Sale(models.Model):
    """Sales transaction header."""
    invoice_number = models.CharField(max_length=30, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sales')
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Sale #{self.invoice_number} - ₱{self.total_amount:,.2f}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number: INV-YYYYMMDD-XXXX
            today = timezone.now().strftime('%Y%m%d')
            last_sale = Sale.objects.filter(
                invoice_number__startswith=f'INV-{today}'
            ).order_by('-invoice_number').first()
            if last_sale:
                last_num = int(last_sale.invoice_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.invoice_number = f'INV-{today}-{new_num:04d}'
        super().save(*args, **kwargs)

    def recalculate_total(self):
        """Recalculate total amount from sale items."""
        total = self.items.aggregate(
            total=models.Sum(models.F('quantity') * models.F('price'))
        )['total'] or 0
        self.total_amount = total
        self.save(update_fields=['total_amount'])


class SaleItem(models.Model):
    """Individual line items within a sale."""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='sale_items')
    product_name = models.CharField(max_length=200)  # Snapshot of product name at time of sale
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)  # Price at time of sale

    @property
    def line_total(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.product_name} x{self.quantity} @ ₱{self.price:,.2f}"

    def save(self, *args, **kwargs):
        # Snapshot product name if not set
        if self.product and not self.product_name:
            self.product_name = self.product.name
        super().save(*args, **kwargs)
