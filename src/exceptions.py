from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

# Логгер для обработки ошибок
logger = logging.getLogger("food_diary_backend")

# 307: Temporary Redirect
async def temporary_redirect_handler(request: Request, exc: HTTPException):
    logger.info(f"Перенаправление 307 (Temporary Redirect) на {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=307,
        content={
            "detail": "Запрос временно перенаправлен на другой URL.",
            "location": exc.headers.get("Location") if exc.headers else None,
        },
        headers=exc.headers  # Если нужно передать заголовки, например "Location"
    )

# Обработчики для конкретных кодов ошибок
# 405: Method Not Allowed
async def method_not_allowed_handler(request: Request, exc: HTTPException):
    logger.error(f"Ошибка 405 (Method Not Allowed) на {request.url}: {str(exc)}")
    return JSONResponse(status_code=405, content={"detail": "Метод не разрешен для этого ресурса"})

# 404: Not Found
async def not_found_handler(request: Request, exc: HTTPException):
    logger.error(f"Ошибка 404 на {request.url}: Ресурс не найден")
    return JSONResponse(status_code=404, content={"detail": "Ресурс не найден"})

# 400: Bad Request
async def bad_request_handler(request: Request, exc: HTTPException):
    logger.error(f"Ошибка 400 (Bad Request) на {request.url}: {str(exc)}")
    return JSONResponse(status_code=400, content={"detail": exc.detail or "Неправильный запрос"})

# 401: Unauthorized
async def unauthorized_handler(request: Request, exc: HTTPException):
    logger.error(f"Ошибка 401 (Unauthorized) на {request.url}: {str(exc)}")
    return JSONResponse(status_code=401, content={"detail": "Неавторизованный доступ"})

# 403: Forbidden
async def forbidden_handler(request: Request, exc: HTTPException):
    logger.error(f"Ошибка 403 (Forbidden) на {request.url}: {str(exc)}")
    return JSONResponse(status_code=403, content={"detail": "Доступ запрещён"})

# Обработчик для ошибок 422 (Unprocessable Entity)
async def unprocessable_entity_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Ошибка 422 (Unprocessable Entity) на {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Ошибка обработки запроса.",
            "errors": exc.errors()  # Детали ошибок валидации
        },
    )

# 500: Internal Server Error
async def internal_server_error_handler(request: Request, exc: Exception):
    logger.error(f"Ошибка 500 (Internal Server Error) на {request.url}: {str(exc)}")
    return JSONResponse(status_code=500, content={"message": "Произошла внутренняя ошибка сервера."})

# Общий обработчик для HTTPException (остальные 400-е и 500-е ошибки)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP ошибка на {request.url}: {str(exc)}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail or "Произошла ошибка."})

# Общий обработчик для всех остальных исключений
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Необработанная ошибка на {request.url}: {str(exc)}")
    return JSONResponse(status_code=500, content={"message": "Произошла ошибка на сервере."})

# 502: Bad Gateway (внешние сервисы)
async def bad_gateway_handler(request: Request, exc: Exception):
    logger.error(f"Ошибка 502 (Bad Gateway) на {request.url}: {str(exc)}")
    return JSONResponse(status_code=502, content={"message": "Ошибка при работе с внешним сервисом."})
