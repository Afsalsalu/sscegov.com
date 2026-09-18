from decimal import Decimal
from .models import WalletTransaction, Wallet, User

def handle_commission(buyer: User, quantity=1):
    """
    When a user buys coupons,
    give commission to the creator (upline).
    """

    if not buyer.created_by:
        # No commission for direct admin or root
        return

    buyer_rate = buyer.pan_rate or Decimal('0')
    creator_rate = buyer.created_by.pan_rate or Decimal('0')

    # Commission per coupon
    commission = (buyer_rate - creator_rate)

    if commission > 0:
        commission_total = commission * quantity

        # Upline wallet update
        upline_wallet, _ = Wallet.objects.get_or_create(user=buyer.created_by)
        upline_wallet.balance += commission_total
        upline_wallet.save()

        # Wallet Transaction record
        WalletTransaction.objects.create(
            user=buyer.created_by,
            amount=commission_total,
            txn_type="credit",
            description=f"Commission from {buyer.username}"
        )
