class InsufficientBalanceError(Exception):
    """Raised when user doesn't have enough balance"""

    pass


class TripNotAvailableError(Exception):
    """Raised when trip is not available for booking"""

    pass


class AuthenticationError(Exception):
    """Raised when authentication fails"""

    pass
