from django.db import transaction
from django.contrib.auth.hashers import check_password

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework import status

from .models import User, Elite, Noob, Wallet
from . import serializers
from .lib.lower_strip import strip_and_lower
from .lib.currency_code import get_currency, get_currency_name
import requests


# Register View
class Register(APIView):
    # authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
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


# Login View
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


# Add Wallet and Get all Wallet View
class Wallets(APIView):
    permission_classes = [IsAuthenticated]

    # Add a wallet for Elite Users
    def post(self, request):
        wallet_data = {
            "currency": request.data["currency"].upper(),
            "balance": 0,
            "main": False,
            "user_id": request.user.id
        }

        # Check if user is an Elite
        try:
            Elite.objects.get(user_id=request.user)

        except Exception:
            return Response(dict(message="You must be an Elite User to create multiple Wallets."),
                            status=status.HTTP_400_BAD_REQUEST)

        # Get all wallets that belong to the user and check if a wallet in that currency exists
        wallets = Wallet.objects.filter(user_id=request.user)
        for wallet in wallets.all():
            if wallet.currency == request.data["currency"].upper():
                return Response(dict(message="You already have a wallet in this currency."),
                                status=status.HTTP_400_BAD_REQUEST)

        wallet_serializer = serializers.WalletSerializer(data=wallet_data)

        if wallet_serializer.is_valid():
            wallet_serializer.save()
            return Response(dict(message="Wallet Created Successfully"), status=status.HTTP_201_CREATED)
        else:
            return Response(
                dict(wallet_serializer.errors),
                status=status.HTTP_400_BAD_REQUEST)

    # Get all wallets that belong to a User
    def get(self, request):
        user = request.user.id

        # Get all wallets that belong to the user
        wallets = Wallet.objects.filter(user_id=user)
        wallets_record = []
        for wallet in wallets.all():
            wallets_record.append(("Currency: " + wallet.currency, "Balance: " + wallet.balance))

        # Get user account
        user_account = User.objects.get(id=user)

        # Get wallet type
        try:
            wallet_type = Elite.objects.get(user_id=request.user).wallet_type

        except Exception:
            wallet_type = Noob.objects.get(user_id=request.user).wallet_type

        wallet_info = {
            "Name": user_account.firstname + " " + user_account.lastname,
            "Wallet Type": wallet_type,
            "Wallets": wallets_record
        }
        return Response(
            wallet_info,
            status=status.HTTP_200_OK
        )


# Fund Wallet View
class FundWallet(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        amount = request.data["amount"]
        amount_currency = request.data["amount_currency"].upper()

        try:
            user_type = Elite.objects.get(user_id=user).wallet_type
        except Exception:
            user_type = Noob.objects.get(user_id=user).wallet_type

        # If User is an elite
        if user_type == 'Elite':

            # Get all wallets that belong to the Elite user and check if a wallet in that currency exists
            wallets = Wallet.objects.filter(user_id=user)
            for wallet in wallets.all():
                if wallet.currency == amount_currency:
                    # sum the balance and the new amount
                    new_balance = float(wallet.balance) + float(amount)
                    funded_wallet = Wallet.objects.get(currency=amount_currency)
                    funding = {
                        "balance": new_balance
                    }
                    # Update Balance in DB
                    wallet_serializer = serializers.WalletSerializer(funded_wallet, data=funding, partial=True)
                    if wallet_serializer.is_valid():
                        wallet_serializer.save()

                        response_data = {
                            "Message": "Wallet funded successfully",
                            "Wallet": wallet.currency,
                            "Balance": new_balance
                        }
                        return Response(
                            response_data,
                            status=status.HTTP_200_OK
                        )
                    else:
                        return Response(
                            dict(wallet_serializer.errors),
                            status=status.HTTP_400_BAD_REQUEST)

                # If currency/wallet does not exist, Create One.
            else:
                balance = amount
                new_wallet = {
                    "user_id": user.id,
                    "currency": amount_currency,
                    "balance": balance,
                    "main": False
                }

                wallet_serializer = serializers.WalletSerializer(data=new_wallet)
                if wallet_serializer.is_valid():
                    wallet_serializer.save()

                    response_data = {
                        "Message": "Wallet Created and funded successfully",
                        "Wallet": amount_currency,
                        "Balance": balance
                    }
                    return Response(
                        response_data,
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        dict(wallet_serializer.errors),
                        status=status.HTTP_400_BAD_REQUEST)

        # If User is a Noob
        if user_type == 'Noob':

            # get instance of user wallet
            wallet = Wallet.objects.get(user_id=user)

            # get main currency from db
            main_curr = wallet.currency

            # get funding currency
            fund_curr = get_currency(amount_currency)

            # generate conversion string
            convert_str = fund_curr+"_"+main_curr

            # get conversion rate
            url = "https://free.currconv.com/api/v7/convert?q="+convert_str+"&compact=ultra&apiKey=066f3d02509dab104f69"
            response = requests.get(url).json()
            rate = response[convert_str]

            print(rate)

            # calculate amount to be funded based on conversion rate
            funding = rate * float(amount)

            # sum the balance and the new amount
            new_balance = float(wallet.balance) + funding

            funding = {
                "balance": new_balance
            }

            # Update Balance in DB
            wallet_serializer = serializers.WalletSerializer(wallet, data=funding, partial=True)
            if wallet_serializer.is_valid():
                wallet_serializer.save()

                response_data = {
                    "Message": "Wallet funded successfully",
                    "Wallet": wallet.currency,
                    "Balance": new_balance
                }
                return Response(
                    response_data,
                    status=status.HTTP_200_OK
                )

        # return Response(
        #     "Yayyyy",
        #     status=status.HTTP_200_OK
        # )
