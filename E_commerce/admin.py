from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, Order, OrderItem  # Correct imports


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'available')
    list_filter = ('category', 'available',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

    def formatted_price(self, obj):
        return format_html("₹ {:,.2f}", obj.price)
    formatted_price.short_description = 'Price'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product', 'quantity', 'price', 'subtotal')
    can_delete = False
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'get_products', 'total_amount', 'city')
    search_fields = ('full_name', 'phone', 'city')
    inlines = [OrderItemInline]

    def get_products(self, obj):
        items = obj.items.all()
        return ", ".join([item.product.name for item in items]) if items else "No products"

    get_products.short_description = "Products Ordered"

    def invoice_link(self, obj):
        if obj.invoice:
            return format_html('<a href="{}" target="_blank">Download</a>', obj.invoice.url)
        return "-"

    invoice_link.short_description = "Invoice"