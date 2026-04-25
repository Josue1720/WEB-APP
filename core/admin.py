from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Product, Sale, SaleItem


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'first_name', 'last_name', 'email', 'role', 'is_active']
    list_filter = ['role', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Contact', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role & Contact', {'fields': ('role', 'phone')}),
    )


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['line_total']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock', 'sku', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'sku']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'user', 'customer_name', 'total_amount', 'date']
    list_filter = ['date', 'user']
    search_fields = ['invoice_number', 'customer_name']
    inlines = [SaleItemInline]
    readonly_fields = ['invoice_number', 'total_amount']


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['sale', 'product_name', 'quantity', 'price', 'line_total']
