import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.models.user import User
from src.schemas.user import UserRead, UserUpdate
from src.services.user_service import find_user_by_login_and_email, delete_user, update_user


@pytest.mark.asyncio
async def test_find_user_by_login_and_email_cache_hit():
    mock_cache = AsyncMock()
    mock_db = AsyncMock()
    email_login = "test_user"

    # Данные, которые вернутся из кэша
    cached_user = {"id": 1, "login": email_login, "email": "test@example.com"}
    mock_cache.get.return_value = cached_user

    with patch("src.services.user_service.cache", mock_cache):
        user = await find_user_by_login_and_email(mock_db, email_login)

        # Проверяем, что данные из кэша возвращаются корректно
        assert user == cached_user
        mock_cache.get.assert_called_once_with(f"user:{email_login}")
        mock_db.execute.assert_not_called()  # База данных не должна вызываться


@pytest.mark.asyncio
async def test_find_user_by_login_and_email_cache_miss():
    mock_cache = AsyncMock()
    mock_db = AsyncMock()
    email_login = "test_user"

    mock_cache.get.return_value = None  # Нет данных в кэше

    # Пользователь из БД
    user_from_db = User(id=1, login=email_login, email="test@example.com")

    # Правильный мок SQLAlchemy execute() -> scalar_one_or_none()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=user_from_db)

    mock_db.execute.return_value = mock_result  # execute() вернёт mock_result

    with patch("src.services.user_service.cache", mock_cache):
        user = await find_user_by_login_and_email(mock_db, email_login)

        assert user.id == user_from_db.id
        assert user.login == user_from_db.login
        assert user.email == user_from_db.email

        mock_cache.get.assert_called_once_with(f"user:{email_login}")

        mock_cache.set.assert_called_once_with(
            f"user:{email_login}",
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

        # Проверяем, что возвращается сам пользователь
        assert deleted_user == user


@pytest.mark.asyncio
async def test_update_user():
    # Создаем моки
    mock_db = AsyncMock()
    mock_cache = AsyncMock()
    mock_find_user = AsyncMock()
    mock_save_weight = AsyncMock()

    # Данные текущего пользователя
    current_user = User(id=1, login="testuser", email="test@example.com", weight=70)

    # Данные для обновления
    user_update = UserUpdate(
        firstname="testusername",
        weight=75,  # Меняем вес
    )

    # Патчим зависимости
    with patch("src.services.user_service.cache", mock_cache):
        with patch("src.services.user_service.find_user_by_login_and_email", mock_find_user):
            with patch("src.services.user_service.save_or_update_weight", mock_save_weight):
                # Настраиваем возвращаемое значение поиска пользователя
                mock_find_user.return_value = current_user

                # Вызываем тестируемую функцию
                updated_user = await update_user(user_update, mock_db, current_user)

                # Проверяем, что `find_user_by_login_and_email` вызван
                mock_find_user.assert_called_once_with(mock_db, "testuser")

                # Проверяем, что обновился firstname
                assert updated_user.firstname == "testusername"

                # Проверяем, что обновился вес
                assert updated_user.weight == 75

                # Проверяем, что был вызван commit
                mock_db.commit.assert_called_once()

                # Проверяем, что был обновлен кэш
                mock_cache.delete.assert_called_once_with("user:testuser")

                # Проверяем, что `save_or_update_weight` вызван при изменении веса
                mock_save_weight.assert_called_once()
