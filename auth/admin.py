"""Админские операции над пользователями.

Здесь и только здесь меняются `plan` и `role`. В схеме `UserUpdate` этих
полей намеренно нет, чтобы через self-service `PATCH /users/me` нельзя было
поднять себе тариф или выдать себе админку.
"""
from typing import List, Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator

from .models import User, UserRead
from .users import UserManager, current_active_user, get_user_manager

router = APIRouter(prefix="/admin", tags=["admin"])

# Допустимые роли. Тариф — свободная строка (тарифы добавляются часто),
# роль — закрытый список, ошибка здесь стоит слишком дорого.
ALLOWED_ROLES = {"user", "admin"}


async def current_admin(user: User = Depends(current_active_user)) -> User:
    """Пускает только пользователей с ролью admin."""
    if user.role != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов",
        )
    return user


class AdminUserUpdate(BaseModel):
    """Тело PATCH: меняем строго plan и/или role, больше ничего."""

    plan: Optional[str] = None
    role: Optional[str] = None

    @field_validator("plan")
    @classmethod
    def _plan_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("plan не может быть пустым")
        return v

    @field_validator("role")
    @classmethod
    def _role_allowed(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if v not in ALLOWED_ROLES:
            raise ValueError(f"role должен быть одним из: {sorted(ALLOWED_ROLES)}")
        return v


@router.get("/users", response_model=List[UserRead], summary="Список пользователей")
async def list_users(
    limit: int = Query(50, ge=1, le=200, description="Сколько записей вернуть"),
    offset: int = Query(0, ge=0, description="Сколько записей пропустить"),
    admin: User = Depends(current_admin),
) -> List[User]:
    """Постраничный список пользователей. Сортировка по id — стабильная,
    иначе при пагинации записи могут дублироваться/пропадать.
    """
    return await User.find_all().sort("_id").skip(offset).limit(limit).to_list()


@router.patch(
    "/users/{user_id}",
    response_model=UserRead,
    summary="Сменить тариф/роль пользователя",
)
async def update_user_plan_role(
    user_id: str,
    payload: AdminUserUpdate,
    admin: User = Depends(current_admin),
    user_manager: UserManager = Depends(get_user_manager),
) -> User:
    """Меняет только plan и/или role указанного пользователя."""
    # Кривой id — это тот же «нет такого пользователя», а не 422.
    try:
        object_id = PydanticObjectId(user_id)
    except Exception:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    target = await User.get(object_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Укажите хотя бы одно поле: plan или role",
        )

    # Защита от выстрела в ногу: сняв админку с самого себя, можно остаться
    # без единого админа и потерять доступ к этому роуту навсегда.
    if (
        "role" in updates
        and updates["role"] != "admin"
        and target.id == admin.id
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Нельзя снять роль admin с самого себя — попросите другого админа",
        )

    # Пишем через адаптер БД fastapi-users, а не через user_manager.update:
    # тот принимает UserUpdate, где plan/role отсутствуют по замыслу.
    return await user_manager.user_db.update(target, updates)
