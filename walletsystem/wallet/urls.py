from django.urls import path
from .views import Register


app_name = "wallet_app"

urlpatterns = [
    path('register', Register.as_view()),
]

