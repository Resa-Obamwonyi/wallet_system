from django.db import transaction
from django.contrib.auth.hashers import check_password

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework import status

from .models import User, Elite, Noob, Wallet, Transactions
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

            # Check for currency in our Available currencies
            valid_currency = get_currency(request.data["main_currency"].upper())

            if not valid_currency == request.data["main_currency"].upper():
                return Response(
                    dict(error=valid_currency + ", Please try a different currency shortcode."),
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
                    "currency": valid_currency,
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

                        # Save transaction to DB
                        transaction_data = {
                            "user_id": request.user.id,
                            "wallet_id": funded_wallet.id,
                            "transaction_type": "Funding",
                            "amount": amount,
                            "currency": amount_currency,
                            "status": "successful"
                        }

                        transaction_serializer = serializers.TransactionSerializer(data=transaction_data)
                        if transaction_serializer.is_valid():
                            transaction_serializer.save()
                        else:
                            return Response(
                                dict(transaction_serializer.errors),
                                status=status.HTTP_400_BAD_REQUEST)

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

                    # Save transaction to DB
                    transaction_data = {
                        "user_id": request.user.id,
                        "wallet_id": wallet_serializer.instance.id,
                        "transaction_type": "Funding",
                        "amount": amount,
                        "currency": amount_currency,
                        "status": "successful"
                    }

                    transaction_serializer = serializers.TransactionSerializer(data=transaction_data)
                    if transaction_serializer.is_valid():
                        transaction_serializer.save()
                    else:
                        return Response(
                            dict(transaction_serializer.errors),
                            status=status.HTTP_400_BAD_REQUEST)

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

                # Save transaction to DB
                transaction_data = {
                    "user_id": request.user.id,
                    "wallet_id": wallet_serializer.instance.id,
                    "transaction_type": "Funding",
                    "amount": amount,
                    "currency": amount_currency,
                    "status": "successful"
                }

                transaction_serializer = serializers.TransactionSerializer(data=transaction_data)
                if transaction_serializer.is_valid():
                    transaction_serializer.save()
                else:
                    return Response(
                        dict(transaction_serializer.errors),
                        status=status.HTTP_400_BAD_REQUEST)

                response_data = {
                    "Message": "Wallet funded successfully",
                    "Wallet": wallet.currency,
                    "Balance": new_balance
                }
                return Response(
                    response_data,
                    status=status.HTTP_200_OK
                )


# Get all transactions that belong to an Account
class TransactionView(APIView):
    permission_classes = [IsAuthenticated]

    # Get all transactions that belong to an Account
    def get(self, request):
        user = request.user.id

        # Get all wallets that belong to the user
        transactions = Transactions.objects.filter(user_id=user)
        transaction_record = []
        for transact in transactions.all():
            transaction_record.append(("Currency: " + transact.currency, "Amount: " + transact.amount,
                                       "Type: " + transact.transaction_type,
                                       "Date: " + transact.created_at.strftime("%m/%d/%Y")))

        # Get user account
        user_account = User.objects.get(id=user)

        # Get wallet type
        try:
            wallet_type = Elite.objects.get(user_id=request.user).wallet_type

        except Exception:
            wallet_type = Noob.objects.get(user_id=request.user).wallet_type

        transaction_info = {
            "Name": user_account.firstname + " " + user_account.lastname,
            "Wallet Type": wallet_type,
            "Transactions": transaction_record
        }
        return Response(
            transaction_info,
            status=status.HTTP_200_OK
        )


# Make withdrawal endpoint
class WithdrawWallet(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        amount = request.data["amount"]
        currency = request.data["currency"].upper()
        user = request.user

        try:
            user_type = Elite.objects.get(user_id=user).wallet_type
        except Exception:
            user_type = Noob.objects.get(user_id=user).wallet_type

        # If User is an elite
        if user_type == 'Elite':

            # For Elite Users with Existing Wallet
            wallets = Wallet.objects.filter(user_id=user)
            for wallet in wallets.all():
                if wallet.currency == currency:

                    # check that the balance is up to the amount to be withdrawn
                    if float(wallet.balance) < float(amount):
                        return Response(
                            dict(errors="Insufficient Funds"),
                            status=status.HTTP_400_BAD_REQUEST)

                    # subtract the amount from the balance
                    new_balance = float(wallet.balance) - float(amount)
                    withdrawn_wallet = Wallet.objects.get(currency=currency)
                    withdrawal = {
                        "balance": new_balance
                    }
                    # Update Balance in DB
                    wallet_serializer = serializers.WalletSerializer(withdrawn_wallet, data=withdrawal, partial=True)
                    if wallet_serializer.is_valid():
                        wallet_serializer.save()

                        # Save transaction to DB
                        transaction_data = {
                            "user_id": request.user.id,
                            "wallet_id": withdrawn_wallet.id,
                            "transaction_type": "Withdrawal",
                            "amount": amount,
                            "currency": currency,
                            "status": "successful"
                        }

                        transaction_serializer = serializers.TransactionSerializer(data=transaction_data)
                        if transaction_serializer.is_valid():
                            transaction_serializer.save()
                        else:
                            return Response(
                                dict(transaction_serializer.errors),
                                status=status.HTTP_400_BAD_REQUEST)

                        response_data = {
                            "Message": "Amount Withdrawn successfully",
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

            # if currency does not exist as a wallet, convert amount to main currency and withdraw
            else:
                wallets = Wallet.objects.filter(user_id=user)
                for wallet in wallets.all():
                    if wallet.main:
                        # get main currency from db
                        main_curr = wallet.currency

                        # get funding currency
                        withdrawal_curr = get_currency(currency)

                        # generate conversion string
                        convert_str = withdrawal_curr + "_" + main_curr

                        # get conversion rate
                        url = "https://free.currconv.com/api/v7/convert?q=" + convert_str + "&compact=ultra&apiKey=066f3d02509dab104f69"
                        response = requests.get(url).json()
                        rate = response[convert_str]

                        # calculate amount to be funded based on conversion rate
                        withdrawal = rate * float(amount)

                        # check that the balance is up to the amount to be withdrawn
                        if float(wallet.balance) < float(withdrawal):
                            return Response(
                                dict(errors="Insufficient Funds"),
                                status=status.HTTP_400_BAD_REQUEST)

                        # Else subtract the amount from the balance
                        new_balance = float(wallet.balance) - float(withdrawal)

                        withdrawal_wallet = {
                            "balance": new_balance
                        }
                        # Update Balance in DB
                        wallet_serializer = serializers.WalletSerializer(wallet, data=withdrawal_wallet,
                                                                         partial=True)
                        if wallet_serializer.is_valid():
                            wallet_serializer.save()

                            # Save transaction to DB
                            transaction_data = {
                                "user_id": request.user.id,
                                "wallet_id": wallet.id,
                                "transaction_type": "Withdrawal",
                                "amount": withdrawal,
                                "currency": wallet.currency,
                                "status": "successful"
                            }

                            transaction_serializer = serializers.TransactionSerializer(data=transaction_data)
                            if transaction_serializer.is_valid():
                                transaction_serializer.save()
                            else:
                                return Response(
                                    dict(transaction_serializer.errors),
                                    status=status.HTTP_400_BAD_REQUEST)

                            response_data = {
                                "Message": "Amount Withdrawn successfully",
                                "Wallet": wallet.currency,
                                "Balance": new_balance
                            }
                            return Response(
                                response_data,
                                status=status.HTTP_200_OK
                            )
        # If User is a Noob
        if user_type == 'Noob':

            # For Noob Users with Existing Wallet they are trying to withdraw from.
            wallet = Wallet.objects.get(user_id=user)
            if wallet.currency == currency:
                # check that the balance is up to the amount to be withdrawn
                if float(wallet.balance) < float(amount):
                    return Response(
                        dict(errors="Insufficient Funds"),
                        status=status.HTTP_400_BAD_REQUEST)

                # subtract the amount from the balance
                new_balance = float(wallet.balance) - float(amount)
                withdrawn_wallet = Wallet.objects.get(currency=currency)
                withdrawal = {
                    "balance": new_balance
                }
                # Update Balance in DB
                wallet_serializer = serializers.WalletSerializer(withdrawn_wallet, data=withdrawal, partial=True)
                if wallet_serializer.is_valid():
                    wallet_serializer.save()

                    # Save transaction to DB
                    transaction_data = {
                        "user_id": request.user.id,
                        "wallet_id": withdrawn_wallet.id,
                        "transaction_type": "Withdrawal",
                        "amount": amount,
                        "currency": currency,
                        "status": "successful"
                    }

                    transaction_serializer = serializers.TransactionSerializer(data=transaction_data)
                    if transaction_serializer.is_valid():
                        transaction_serializer.save()
                    else:
                        return Response(
                            dict(transaction_serializer.errors),
                            status=status.HTTP_400_BAD_REQUEST)

                    response_data = {
                        "Message": "Amount Withdrawn successfully",
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

            # if currency does not exist as a wallet, convert amount to main currency and withdraw
            else:
                wallets = Wallet.objects.filter(user_id=user)
                for wallet in wallets.all():
                    if wallet.main:
                        # get main currency from db
                        main_curr = wallet.currency

                        # get funding currency
                        withdrawal_curr = get_currency(currency)

                        # generate conversion string
                        convert_str = withdrawal_curr + "_" + main_curr

                        # get conversion rate
                        url = "https://free.currconv.com/api/v7/convert?q=" + convert_str + "&compact=ultra&apiKey=066f3d02509dab104f69"
                        response = requests.get(url).json()
                        rate = response[convert_str]

                        # calculate amount to be funded based on conversion rate
                        withdrawal = rate * float(amount)

                        # check that the balance is up to the amount to be withdrawn
                        if float(wallet.balance) < float(withdrawal):
                            return Response(
                                dict(errors="Insufficient Funds"),
                                status=status.HTTP_400_BAD_REQUEST)

                        # Else subtract the amount from the balance
                        new_balance = float(wallet.balance) - float(withdrawal)

                        withdrawal_wallet = {
                            "balance": new_balance
                        }
                        # Update Balance in DB
                        wallet_serializer = serializers.WalletSerializer(wallet, data=withdrawal_wallet,
                                                                         partial=True)
                        if wallet_serializer.is_valid():
                            wallet_serializer.save()

                            # Save transaction to DB
                            transaction_data = {
                                "user_id": request.user.id,
                                "wallet_id": wallet.id,
                                "transaction_type": "Withdrawal",
                                "amount": withdrawal,
                                "currency": wallet.currency,
                                "status": "successful"
                            }

                            transaction_serializer = serializers.TransactionSerializer(data=transaction_data)
                            if transaction_serializer.is_valid():
                                transaction_serializer.save()
                            else:
                                return Response(
                                    dict(transaction_serializer.errors),
                                    status=status.HTTP_400_BAD_REQUEST)

                            response_data = {
                                "Message": "Amount Withdrawn successfully",
                                "Wallet": wallet.currency,
                                "Balance": new_balance
                            }
                            return Response(
                                response_data,
                                status=status.HTTP_200_OK
                            )
            return Response(
                "I said I am a NOOB",
                status=status.HTTP_400_BAD_REQUEST
            )

