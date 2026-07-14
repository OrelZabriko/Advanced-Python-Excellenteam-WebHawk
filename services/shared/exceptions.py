class ServiceError(Exception):
    """
    Raised for expected business-logic failures (bad input, auth failure,
    duplicate resource, not found, etc.) across any WebHawk Python service.

    Carries an HTTP status_code so routes can translate it directly into
    a response, instead of every route re-deciding what status code fits
    each error message.
    """
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code