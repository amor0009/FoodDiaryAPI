import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from src.models.user import User
from src.schemas.user import UserRead, UserUpdate
from src.schemas.user_weight import UserWeightUpdate
from src.services.user_service import find_user_by_login_and_email, delete_user, update_user

@pytest.mark.asyncio
async def test_find_user_by_login_and_email_cache_hit():
    mock_cache = AsyncMock()
    mock_db = AsyncMock()
    login = "test_user"
    email = None

    # Данные, которые вернутся из кэша
    cached_user = {"id": 1, "login": login, "email": "test@example.com"}
    mock_cache.get.return_value = cached_user

    with patch("src.services.user_service.cache", mock_cache):
        user = await find_user_by_login_and_email(mock_db, login)

        expected_user = UserRead.model_validate(cached_user)

        # Проверяем, что данные из кэша возвращаются корректно
        assert user == expected_user
        mock_cache.get.assert_called_once_with(f"user:{login}")
        mock_db.execute.assert_not_called()  # База данных не должна вызываться

@pytest.mark.asyncio
async def test_find_user_by_login_and_email_cache_miss():
    mock_cache = AsyncMock()
    mock_db = AsyncMock()
    login = "test_user"
    email = None

    mock_cache.get.return_value = None  # Нет данных в кэше

    # Пользователь из БД
    user_from_db = User(id=1, login=login, email="test@example.com")

    # Правильный мок SQLAlchemy execute() -> scalar_one_or_none()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=user_from_db)

    mock_db.execute.return_value = mock_result  # execute() вернёт mock_result

    with patch("src.services.user_service.cache", mock_cache):
        user = await find_user_by_login_and_email(mock_db, login)

        assert user.id == user_from_db.id
        assert user.login == user_from_db.login
        assert user.email == user_from_db.email

        mock_cache.get.assert_called_once_with(f"user:{login}")

        mock_cache.set.assert_called_once_with(
            f"user:{login}",
            UserRead.model_validate(user_from_db).model_dump(mode="json"),
            expire=3600,
        )

@pytest.mark.asyncio
async def test_delete_user():
    # Создаем моки
    mock_db = AsyncMock()
    mock_cache = AsyncMock()

    # Пользователь для удаления
    user = User(id=1, login="testuser", email="test@example.com")

    # Патчим кэш
    with patch("src.services.user_service.cache", mock_cache):
        # Вызываем тестируемую функцию
        deleted_user = await delete_user(mock_db, user)

        # Проверяем, что удаление из базы вызвано
        mock_db.delete.assert_called_once_with(user)

        # Проверяем, что был вызван commit
        mock_db.commit.assert_called_once()

        # Проверяем, что пользователь удаляется из кэша
        mock_cache.delete.assert_called_once_with("user:testuser")

        expected_user = UserRead.model_validate(user)

        # Проверяем, что возвращается сам пользователь
        assert deleted_user == expected_user

@pytest.mark.asyncio
async def test_update_user():
    # Моки для кэша и базы данных
    mock_cache = AsyncMock()
    mock_db = AsyncMock()
    email_login = "test_user"

    # Текущий пользователь, который будет обновлен
    current_user = User(
        id=1,
        login=email_login,
        email="test@example.com",
        firstname="oldname",
        lastname="oldlastname",
        age=25,
        height=180,
        weight=70,
        gender="male",
        aim="maintain",
        recommended_calories=2500,
    )

    # Данные для обновления
    user_update = UserUpdate(
        firstname="newname",
        lastname="newlastname",
        age=26,
        height=185,
        weight=75,
        gender="female",
        aim="lose",
        recommended_calories=2300,
    )

    # Мокируем запрос и результат
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=current_user)  # Возвращаем объект пользователя

    # Настроим мок на выполнение запроса
    mock_db.execute.return_value = mock_result  # Это имитирует выполнение запроса

    # Мокируем commit
    mock_db.commit = AsyncMock()

    # Мокируем функцию для сохранения/обновления веса
    mock_save_weight = AsyncMock()

    # Патчим зависимости
    with patch("src.services.user_service.cache", mock_cache):
        with patch("src.services.user_service.save_or_update_weight", mock_save_weight):
            # Вызываем тестируемую функцию
            updated_user = await update_user(user_update, mock_db, current_user)

            # Проверяем, что данные пользователя были обновлены
            assert updated_user.firstname == "newname"
            assert updated_user.lastname == "newlastname"
            assert updated_user.age == 26
            assert updated_user.height == 185
            assert updated_user.weight == 75
            assert updated_user.gender == "female"
            assert updated_user.aim == "lose"
            assert updated_user.recommended_calories == 2300

            # Проверяем, что был вызван commit
            mock_db.commit.assert_called_once()

            # Проверяем, что данные были обновлены в кэше
            mock_cache.delete.assert_called_once_with(f"user:{current_user.login}")

            # Проверяем, что функция обновления веса была вызвана
            mock_save_weight.assert_called_once_with(
                UserWeightUpdate(user_id=current_user.id, weight=user_update.weight),
                mock_db,
                current_user.id
            )

            # Проверяем, что было выполнено обновление данных пользователя
            mock_db.execute.return_value.scalar_one_or_none.assert_called_once()

    # Проверяем обработку ошибки, если пользователь не найден
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    with pytest.raises(HTTPException):
        await update_user(user_update, mock_db, current_user)