from django.shortcuts import render
from django.db import transaction
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework import authentication, permissions
from rest_framework import status

from .models import User, Elite, Noob, Wallet
from . import serializers
from .lib.lower_strip import strip_and_lower


class Register(APIView):
    # authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
    # try:
        with transaction.atomic():

            if not (request.data.get('firstname', '') or len(request.data.get('firstname', '') > 3)):
                return Response(
                    dict(error='Invalid Firstname, Firstname must be at least three Characters long.'),
                    status=status.HTTP_400_BAD_REQUEST)

            if not (request.data.get('lastname', '') or len(request.data.get('lastname', '') > 3)):
                return Response(
                    dict(error='Invalid Lastname, Lastname must be at least three Characters long.'),
                    status=status.HTTP_400_BAD_REQUEST)

            user_data = {
                "firstname": request.data["firstname"],
                "lastname": request.data["lastname"],
                "email": request.data["email"],
                "password": request.data["password"]
            }
            user_serializer = serializers.UserSerializer(data=user_data)

            if user_serializer.is_valid():
                user = user_serializer.save()
                user.set_password(request.data["password"])

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
                        return Response(
                            dict(elite_serializer.errors),
                            status=status.HTTP_400_BAD_REQUEST)

                if request.data['wallet_type'].capitalize() == 'Noob':
                    noob_serializer = serializers.NoobSerializer(data=wallet_data)
                    if noob_serializer.is_valid():
                        noob_serializer.save()
                    else:
                        return Response(
                            dict(noob_serializer.errors),
                            status=status.HTTP_400_BAD_REQUEST)

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
                    return Response(
                        dict(wallet_serializer.errors),
                        status=status.HTTP_400_BAD_REQUEST)

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
        #
        # except Exception as err:
        #     return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Login(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            email = strip_and_lower(request.data.get('email', ''))
            password = request.data.get('password', '')

            if email is None or password is None:
                return Response(
                    dict(invalid_credential='Please provide both email and password'),
                    status=status.HTTP_400_BAD_REQUEST)

            # hash_password = make_password(password)
            db_user = User.objects.get(email=email)
            user = check_password(password, db_user.password)

            if not user:
                return Response(
                    dict(invalid_credential='Please ensure that your email and password are correct'),
                    status=status.HTTP_400_BAD_REQUEST)

            token, _ = Token.objects.get_or_create(user=db_user)
            return Response(dict(token=token.key), status=status.HTTP_200_OK)

        except Exception as err:
            return Response(dict(error=err), status=status.HTTP_400_BAD_REQUEST)


