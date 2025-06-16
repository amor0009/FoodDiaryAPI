from fastapi import HTTPException, status

CredentialsException = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials."
)
TokenDoesntExist = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token doesn't exist."
)
TokenHasExpired = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token has expired."
)
InvalidToken = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid token."
)
UserDoesntExist = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="User doesn't exist."
)

StaffDoesntExist = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Staff doesn't exist."
)

CacheGetError = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Cache get error."
)
CacheSetError = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Cache set error."
)
CacheDeleteError = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Cache delete error. Redis connection is not established."
)

RabbitMQChannelError = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="RabbitMQ channel isn't connected."
)


class CustomExceptions:
    @classmethod
    def raise_password_validation_error(
        cls,
        errors: list[str],
        min_length: int = 8,
        require_upper: bool = True,
        require_lower: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
        special_chars: str = "!@#$%^&*"
    ):
        """Вызывает HTTPException с детальной информацией о валидации пароля"""
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Weak password",
                "errors": errors,
                "requirements": {
                    "min_length": min_length,
                    "require_upper": require_upper,
                    "require_lower": require_lower,
                    "require_digit": require_digit,
                    "require_special": require_special,
                    "special_chars": special_chars
                }
            }
        )
