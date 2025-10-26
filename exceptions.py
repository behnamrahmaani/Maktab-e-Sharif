class InsufficientBalanceError(Exception):
    """Raised when user doesn't have enough balance for a purchase"""

    pass


class TripNotAvailableError(Exception):
    """Raised when trying to book a trip that's not available"""

    pass


class SeatNotAvailableError(Exception):
    """Raised when trying to book an unavailable seat"""

    pass


class AuthenticationError(Exception):
    """Raised when authentication fails"""

    pass


class AuthorizationError(Exception):
    """Raised when user doesn't have permission"""

    pass
