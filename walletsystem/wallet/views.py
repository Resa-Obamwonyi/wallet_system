from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework import status
from .models import User, Elite, Noob, Wallet
from . import serializers
from django.db import transaction

# Create your views here.
class Register(APIView):
    # authentication_classes = [authentication.TokenAuthentication]

    def post(self, request):
        try:
            with transaction.atomic():

                user_data = {
                    "firstname": request.data["firstname"],
                    "lastname": request.data["lastname"],
                    "email": request.data["email"],
                    "password": request.data["password"]
                }
                user_serializer = serializers.UserSerializer(data=user_data)

                if user_serializer.is_valid():
                    user = user_serializer.save()

                    wallet_data = {
                        "user_id": user.id,
                        "wallet_type": request.data["wallet_type"],
                        "main_currency": request.data["main_currency"]
                    }

                    if request.data['wallet_type'].capitalize() == 'Elite':
                        elite_serializer = serializers.EliteSerializer(data=wallet_data)
                        if elite_serializer.is_valid():
                            elite_serializer.save()
                        else:
                            raise Exception (elite_serializer.errors)

                    if request.data['wallet_type'].capitalize() == 'Noob':
                        noob_serializer = serializers.NoobSerializer(data=wallet_data)
                        if noob_serializer.is_valid():
                            noob_serializer.save()
                        else:
                            raise Exception(noob_serializer.errors)

                    default_wallet = {
                        "user_id": user.id,
                        "currency": request.data["main_currency"],
                        "balance": 0,
                        "main": True
                    }

                    wallet_serializer = serializers.WalletSerializer(data=default_wallet)
                    if wallet_serializer.is_valid():
                        wallet_serializer.save()
                    else:
                        raise Exception(wallet_serializer.errors)

                    profile_data = {
                        "user_id": user.id,
                        "firstname": request.data["firstname"],
                        "lastname": request.data["lastname"],
                        "email": request.data["email"],
                        "wallet_type": request.data["wallet_type"],
                        "main_currency": request.data["main_currency"]
                    }

                    return Response(
                        profile_data,
                        status=status.HTTP_201_CREATED)
                else:
                    return Response(
                        user_serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)
        except Exception as err:
            print(err)
            return Response(dict(errors=err), status=status.HTTP_400_BAD_REQUEST)
