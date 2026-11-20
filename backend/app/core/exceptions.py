"""
Centralized exceptions and HTTP error handlers for FastAPI.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse


class StarAppException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, error_code: str = "BAD_REQUEST"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class NotFoundException(StarAppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND, "NOT_FOUND")


class UnauthorizedException(StarAppException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED")


class ForbiddenException(StarAppException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status.HTTP_403_FORBIDDEN, "FORBIDDEN")


class ConflictException(StarAppException):
    def __init__(self, message: str = "Resource state conflict"):
        super().__init__(message, status.HTTP_409_CONFLICT, "CONFLICT")


async def starapp_exception_handler(request: Request, exc: StarAppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
            }
        }
    )
