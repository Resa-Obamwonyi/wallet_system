from django.urls import path
from .views import Register, Login, Wallets, FundWallet, TransactionView, WithdrawWallet, RegisterAdmin,\
    PendingWithdrawal, ApproveWithdrawal, PromoteUser, DemoteUser


# app_name = "wallet_app"

urlpatterns = [
    path('register', Register.as_view(), name='register_user'),
    path('login', Login.as_view(), name='login_user'),
    path('add_wallet', Wallets.as_view(), name='add_user_wallet'),
    path('get_wallet', Wallets.as_view(), name='get_user_wallet'),
    path('fund_wallet', FundWallet.as_view(), name='fund_user_wallet'),
    path('transactions', TransactionView.as_view(), name='get_transactions'),
    path('withdraw', WithdrawWallet.as_view(), name='make_withdrawals'),
    path('register-admin', RegisterAdmin.as_view(), name='register_admin'),
    path('pending', PendingWithdrawal.as_view(), name='pending_withdrawal'),
    path('approve-withdrawal', ApproveWithdrawal.as_view(), name='approve_withdrawal'),
    path('promote-user', PromoteUser.as_view(), name='promote_user'),
    path('demote-user', DemoteUser.as_view(), name='demote_user'),
]

