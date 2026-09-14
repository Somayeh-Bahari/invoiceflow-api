from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, InvoiceViewSet


router = DefaultRouter()
router.register("customers", CustomerViewSet)
router.register("invoices", InvoiceViewSet, basename="invoice")


urlpatterns = [
    path("", include(router.urls)),
]