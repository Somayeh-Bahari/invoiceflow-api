from django.contrib import admin
from .models import Customer, Invoice


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "created_at")
    search_fields = ("name", "email", "phone")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "customer",
        "amount",
        "status",
        "issue_date",
        "due_date",
        "created_by",
    )

    list_filter = ("status", "issue_date", "due_date")
    search_fields = ("invoice_number", "customer__name")