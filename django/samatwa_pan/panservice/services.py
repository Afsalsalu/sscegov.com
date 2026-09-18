from django.db import transaction
from .models import Wallet, WalletTransaction

@transaction.atomic
def create_wallet_transaction(user, amount, txn_type, description):
    wallet, _ = Wallet.objects.get_or_create(user = user)

    opening_balance = wallet.balance

    if txn_type == 'credit':
        closing_balance = opening_balance + amount
    else:
        if opening_balance < amount:
            raise ValueError('Insufficient balance')
        closing_balance = opening_balance - amount

    wallet.balance = closing_balance
    wallet.save()

    txn = WalletTransaction.objects.create(
        user=user,
        amount=amount,
        txn_type=txn_type,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        description=description
    )

    return txn