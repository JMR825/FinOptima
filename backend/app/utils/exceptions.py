"""Custom exceptions for market data and ML pipeline errors."""


class PortfolioOptimizerError(Exception):
    """Base exception for portfolio optimizer errors."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class APIKeyMissingError(PortfolioOptimizerError):
    def __init__(self):
        super().__init__(
            "Alpha Vantage API key is missing. Set ALPHA_VANTAGE_API_KEY in .env or use sample data mode.",
            code="API_KEY_MISSING",
        )


class APIRateLimitError(PortfolioOptimizerError):
    def __init__(self, message: str = "API rate limit reached. Using fallback sample data."):
        super().__init__(message, code="API_RATE_LIMIT")


class InvalidSymbolError(PortfolioOptimizerError):
    def __init__(self, symbol: str):
        super().__init__(f"Invalid or unknown stock symbol: {symbol}", code="INVALID_SYMBOL")


class InsufficientDataError(PortfolioOptimizerError):
    def __init__(self, symbol: str, required: int, actual: int):
        super().__init__(
            f"Insufficient data for {symbol}: need at least {required} rows, got {actual}.",
            code="INSUFFICIENT_DATA",
        )
