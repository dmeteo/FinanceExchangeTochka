class InsufficientBalanceException(Exception):
    def __init__(self, message="Insufficient balance for transfer"):
        self.message = message
        super().__init__(self.message)