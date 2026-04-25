from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Sales
    path('sales/new/', views.record_sale, name='record_sale'),
    path('sales/history/', views.sales_history, name='sales_history'),
    path('sales/<int:pk>/', views.sale_detail, name='sale_detail'),

    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/export/csv/', views.export_sales_csv, name='export_csv'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),

    # Restocking
    path('restock/', views.restock_list, name='restock_list'),
    path('restock/add/', views.restock_create, name='restock_create'),

    # Cash Logs
    path('cash-log/', views.cash_log_list, name='cash_log_list'),
    path('cash-log/add/', views.cash_log_create, name='cash_log_create'),

    # Users
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),

    # API
    path('api/product/<int:pk>/price/', views.api_product_price, name='api_product_price'),
]
