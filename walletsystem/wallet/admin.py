from django.contrib import admin
from .models import User, Elite, Noob, Wallet, Transactions

# Register your models here.
admin.site.register(User)
admin.site.register(Elite)
admin.site.register(Noob)
admin.site.register(Wallet)
admin.site.register(Transactions)
