from rest_framework.exceptions import APIException
from rest_framework import status

class UnauthorizedAccessException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Unauthorized to access this appointment.'
    default_code = 'forbidden'

    def __init__(self, detail=None, code=None):
        if detail is not None:
            self.detail = detail
        else:
            self.detail = self.default_detail
        if code is not None:
            self.code = code
        else:
            self.code = self.default_code