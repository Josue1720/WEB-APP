import json
import csv
import io
from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone
from django.core.paginator import Paginator

from .models import User, Product, Sale, SaleItem
from .forms import (
    LoginForm, UserCreateForm, UserEditForm,
    ProductForm, SaleForm,
)
from .decorators import role_required


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
def login_view(request):
    """User login page."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    """Log the user out."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
@login_required
def dashboard(request):
    """Main dashboard with KPIs and charts."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    # Base queryset — staff see only their own sales
    base_qs = Sale.objects.all()
    if request.user.role == 'staff':
        base_qs = base_qs.filter(user=request.user)

    sales_today = base_qs.filter(date__gte=today_start).aggregate(
        total=Sum('total_amount'), count=Count('id')
    )
    sales_week = base_qs.filter(date__gte=week_start).aggregate(
        total=Sum('total_amount'), count=Count('id')
    )
    sales_month = base_qs.filter(date__gte=month_start).aggregate(
        total=Sum('total_amount'), count=Count('id')
    )

    # Top products (last 30 days)
    top_products = (
        SaleItem.objects
        .filter(sale__date__gte=now - timedelta(days=30))
        .values('product_name')
        .annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price'))
        )
        .order_by('-total_qty')[:5]
    )

    # Daily sales for chart (last 14 days)
    daily_sales = (
        base_qs
        .filter(date__gte=now - timedelta(days=14))
        .annotate(day=TruncDate('date'))
        .values('day')
        .annotate(total=Sum('total_amount'), count=Count('id'))
        .order_by('day')
    )
    chart_labels = [d['day'].strftime('%b %d') for d in daily_sales]
    chart_data = [float(d['total'] or 0) for d in daily_sales]

    # Recent sales
    recent_sales = base_qs[:10]

    context = {
        'sales_today': sales_today,
        'sales_week': sales_week,
        'sales_month': sales_month,
        'top_products': top_products,
        'recent_sales': recent_sales,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    }
    return render(request, 'core/dashboard.html', context)


# ─────────────────────────────────────────────
# RECORD SALE
# ─────────────────────────────────────────────
@login_required
def record_sale(request):
    """Page to record a new sale with dynamic line items."""
    products = Product.objects.filter(is_active=True)
    if request.method == 'POST':
        form = SaleForm(request.POST)
        items_json = request.POST.get('items_data', '[]')
        try:
            items_data = json.loads(items_json)
        except json.JSONDecodeError:
            items_data = []

        if form.is_valid() and items_data:
            sale = form.save(commit=False)
            sale.user = request.user
            sale.save()

            for item in items_data:
                product = Product.objects.get(id=item['product_id'])
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    product_name=product.name,
                    quantity=int(item['quantity']),
                    price=Decimal(str(item['price'])),
                )
                # Decrease stock
                if product.stock >= int(item['quantity']):
                    product.stock -= int(item['quantity'])
                    product.save(update_fields=['stock'])

            sale.recalculate_total()
            messages.success(request, f'Sale {sale.invoice_number} recorded successfully! Total: ₱{sale.total_amount:,.2f}')
            return redirect('sale_detail', pk=sale.pk)
        else:
            if not items_data:
                messages.error(request, 'Please add at least one item to the sale.')
    else:
        form = SaleForm()

    products_json = json.dumps([
        {'id': p.id, 'name': p.name, 'price': float(p.price), 'stock': p.stock}
        for p in products
    ])
    return render(request, 'core/record_sale.html', {
        'form': form,
        'products_json': products_json,
    })


@login_required
def sale_detail(request, pk):
    """View a single sale receipt."""
    sale = get_object_or_404(Sale, pk=pk)
    # Staff can only see their own sales
    if request.user.role == 'staff' and sale.user != request.user:
        messages.error(request, "You don't have permission to view this sale.")
        return redirect('sales_history')
    return render(request, 'core/sale_detail.html', {'sale': sale})


# ─────────────────────────────────────────────
# SALES HISTORY
# ─────────────────────────────────────────────
@login_required
def sales_history(request):
    """Searchable, filterable sales history table."""
    qs = Sale.objects.select_related('user').all()

    # Staff see only their own
    if request.user.role == 'staff':
        qs = qs.filter(user=request.user)

    # Filters
    search = request.GET.get('search', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    staff_filter = request.GET.get('staff', '')
    sort_by = request.GET.get('sort', '-date')

    if search:
        qs = qs.filter(
            Q(invoice_number__icontains=search) |
            Q(customer_name__icontains=search)
        )
    if date_from:
        qs = qs.filter(date__date__gte=date_from)
    if date_to:
        qs = qs.filter(date__date__lte=date_to)
    if staff_filter:
        qs = qs.filter(user_id=staff_filter)

    # Sorting
    allowed_sorts = ['date', '-date', 'total_amount', '-total_amount']
    if sort_by in allowed_sorts:
        qs = qs.order_by(sort_by)

    paginator = Paginator(qs, 20)
    page = request.GET.get('page', 1)
    sales = paginator.get_page(page)

    staff_list = User.objects.all().order_by('first_name')

    context = {
        'sales': sales,
        'staff_list': staff_list,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
        'staff_filter': staff_filter,
        'sort_by': sort_by,
    }
    return render(request, 'core/sales_history.html', context)


# ─────────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────────
@login_required
@role_required('admin', 'manager')
def reports(request):
    """Reports page with charts and export options."""
    now = timezone.now()
    period = request.GET.get('period', 'daily')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    qs = Sale.objects.all()

    if date_from:
        qs = qs.filter(date__date__gte=date_from)
    if date_to:
        qs = qs.filter(date__date__lte=date_to)

    # Summary stats
    summary = qs.aggregate(
        total_revenue=Sum('total_amount'),
        total_transactions=Count('id'),
    )

    # Grouped data for chart
    if period == 'weekly':
        grouped = (
            qs.annotate(period=TruncWeek('date'))
            .values('period')
            .annotate(total=Sum('total_amount'), count=Count('id'))
            .order_by('period')
        )
    elif period == 'monthly':
        grouped = (
            qs.annotate(period=TruncMonth('date'))
            .values('period')
            .annotate(total=Sum('total_amount'), count=Count('id'))
            .order_by('period')
        )
    else:
        grouped = (
            qs.annotate(period=TruncDate('date'))
            .values('period')
            .annotate(total=Sum('total_amount'), count=Count('id'))
            .order_by('period')
        )

    chart_labels = [g['period'].strftime('%b %d, %Y') if g['period'] else '' for g in grouped]
    chart_data = [float(g['total'] or 0) for g in grouped]
    chart_counts = [g['count'] for g in grouped]

    # Product performance
    product_performance = (
        SaleItem.objects
        .filter(sale__in=qs)
        .values('product_name')
        .annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price'))
        )
        .order_by('-total_revenue')[:10]
    )
    product_labels = [p['product_name'] for p in product_performance]
    product_revenue = [float(p['total_revenue'] or 0) for p in product_performance]

    # Staff performance
    staff_performance = (
        qs.values('user__first_name', 'user__last_name', 'user__username')
        .annotate(
            total_sales=Sum('total_amount'),
            transaction_count=Count('id')
        )
        .order_by('-total_sales')[:10]
    )

    context = {
        'summary': summary,
        'period': period,
        'date_from': date_from,
        'date_to': date_to,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'chart_counts': json.dumps(chart_counts),
        'product_labels': json.dumps(product_labels),
        'product_revenue': json.dumps(product_revenue),
        'product_performance': product_performance,
        'staff_performance': staff_performance,
    }
    return render(request, 'core/reports.html', context)


@login_required
@role_required('admin', 'manager')
def export_sales_csv(request):
    """Export sales data as CSV (Excel-compatible)."""
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    qs = Sale.objects.select_related('user').prefetch_related('items').all()
    if date_from:
        qs = qs.filter(date__date__gte=date_from)
    if date_to:
        qs = qs.filter(date__date__lte=date_to)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Invoice #', 'Date', 'Staff', 'Customer',
        'Product', 'Qty', 'Unit Price', 'Line Total', 'Sale Total', 'Notes'
    ])

    for sale in qs:
        for item in sale.items.all():
            writer.writerow([
                sale.invoice_number,
                sale.date.strftime('%Y-%m-%d %H:%M'),
                sale.user.get_full_name() if sale.user else 'N/A',
                sale.customer_name or '',
                item.product_name,
                item.quantity,
                float(item.price),
                float(item.line_total),
                float(sale.total_amount),
                sale.notes or '',
            ])

    return response


# ─────────────────────────────────────────────
# PRODUCT MANAGEMENT
# ─────────────────────────────────────────────
@login_required
@role_required('admin', 'manager')
def product_list(request):
    """List all products."""
    products = Product.objects.all()
    search = request.GET.get('search', '').strip()
    if search:
        products = products.filter(Q(name__icontains=search) | Q(sku__icontains=search))

    paginator = Paginator(products, 20)
    page = request.GET.get('page', 1)
    products = paginator.get_page(page)
    return render(request, 'core/product_list.html', {'products': products, 'search': search})


@login_required
@role_required('admin', 'manager')
def product_create(request):
    """Create a new product."""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product created successfully!')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'core/product_form.html', {'form': form, 'title': 'Add Product'})


@login_required
@role_required('admin', 'manager')
def product_edit(request, pk):
    """Edit an existing product."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'core/product_form.html', {'form': form, 'title': 'Edit Product'})


@login_required
@role_required('admin')
def product_delete(request, pk):
    """Delete a product."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted.')
        return redirect('product_list')
    return render(request, 'core/product_confirm_delete.html', {'product': product})


# ─────────────────────────────────────────────
# USER MANAGEMENT
# ─────────────────────────────────────────────
@login_required
@role_required('admin')
def user_list(request):
    """List all users (admin only)."""
    users = User.objects.all().order_by('role', 'first_name')
    return render(request, 'core/user_list.html', {'users': users})


@login_required
@role_required('admin')
def user_create(request):
    """Create a new user."""
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'User created successfully!')
            return redirect('user_list')
    else:
        form = UserCreateForm()
    return render(request, 'core/user_form.html', {'form': form, 'title': 'Add User'})


@login_required
@role_required('admin')
def user_edit(request, pk):
    """Edit an existing user."""
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated successfully!')
            return redirect('user_list')
    else:
        form = UserEditForm(instance=user_obj)
    return render(request, 'core/user_form.html', {'form': form, 'title': f'Edit User: {user_obj.username}'})


@login_required
@role_required('admin')
def user_delete(request, pk):
    """Delete a user."""
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('user_list')
    if request.method == 'POST':
        user_obj.delete()
        messages.success(request, 'User deleted.')
        return redirect('user_list')
    return render(request, 'core/user_confirm_delete.html', {'user_obj': user_obj})


# ─────────────────────────────────────────────
# API ENDPOINTS (for AJAX)
# ─────────────────────────────────────────────
@login_required
def api_product_price(request, pk):
    """Return product price as JSON (for dynamic sale form)."""
    product = get_object_or_404(Product, pk=pk)
    return JsonResponse({'price': float(product.price), 'name': product.name, 'stock': product.stock})
