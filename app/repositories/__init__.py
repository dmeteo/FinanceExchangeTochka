from .user import UserRepository
from .instrument import InstrumentRepository
from .balance import BalanceRepository
from .order import OrderRepository
from .transaction import TransactionRepository

user_repo = UserRepository()
instrument_repo = InstrumentRepository()
balance_repo = BalanceRepository()
order_repo = OrderRepository()
transaction_repo = TransactionRepository()

__all__ = [
    "user_repo",
    "instrument_repo",
    "balance_repo",
    "order_repo",
    "transaction_repo"
]