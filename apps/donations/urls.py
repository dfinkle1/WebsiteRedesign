from django.urls import path

from . import views

app_name = "donations"

urlpatterns = [
    path("donate/", views.donate_view, name="donate"),
    path("donate/paypal/return/", views.paypal_return_view, name="paypal_return"),
    path("donate/paypal/cancel/", views.paypal_cancel_view, name="paypal_cancel"),
    path("donate/paypal/webhook/", views.PayPalWebhookView.as_view(), name="paypal_webhook"),
]
