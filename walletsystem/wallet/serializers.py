from rest_framework import serializers
from .models import User, Elite, Noob, Wallet, Transactions
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password


class UserSerializer(serializers.ModelSerializer):
    """ Serializes our user data"""

    class Meta:
        model = User
        fields = '__all__'

    def validate(self, data):
        email_validation = 'email' in data and data['email']
        validate_password(password=data['password'].strip())
        errors = {}

        if not email_validation:
            errors['email'] = ['Invalid email']

        if len(errors):
            raise serializers.ValidationError(errors)

        # hash password
        data['password'] = make_password(data.get('password'))
        saved_data = {
            'firstname': data['firstname'],
            'lastname': data['lastname'],
            'email': data['email'],
            'password': data['password']
        }

        return saved_data


class EliteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Elite
        fields = '__all__'


class NoobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Noob
        fields = '__all__'


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transactions
        fields = '__all__'
