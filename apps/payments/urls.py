from django.urls import path

from .views import (
    PremiumView,
    SubscriptionPlansView,
    activate_premium_stub,
    activate_weekend_stub,
    activate_weekly_stub,
    kiba_create_payment,
    kiba_payment_status,
    kibawallet_webhook,
    rewarded_ad_complete,
    rewarded_ad_status,
    watch_ad_reward,
)

app_name = "payments"

urlpatterns = [
    path("plans/", SubscriptionPlansView.as_view(), name="plans"),
    path("premium/", PremiumView.as_view(), name="premium"),
    path("api/rewarded-ad/complete/", rewarded_ad_complete, name="rewarded_ad_complete"),
    path("api/rewarded-ad/status/", rewarded_ad_status, name="rewarded_ad_status"),
    path("api/activate-weekly/", activate_weekly_stub, name="activate_weekly"),
    path("api/activate-weekend/", activate_weekend_stub, name="activate_weekend"),
    path("ad-reward/", watch_ad_reward, name="ad_reward"),
    path("activate-stub/", activate_premium_stub, name="activate_stub"),
    path("api/kiba/create/", kiba_create_payment, name="kiba_create"),
    path("api/kiba/status/<int:transaction_id>/", kiba_payment_status, name="kiba_status"),
    path("webhooks/kibawallet/", kibawallet_webhook, name="kiba_webhook"),
]
