from django.urls import path
from .views import Register, Login


app_name = "wallet_app"

urlpatterns = [
    path('register', Register.as_view()),
    path('login', Login.as_view()),
]

