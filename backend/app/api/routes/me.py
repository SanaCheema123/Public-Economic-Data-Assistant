from fastapi import APIRouter, Depends

from app.models.entities import User
from app.schemas.auth import UserOut
from app.security.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["User"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id, full_name=user.full_name, email=user.email,
        preferred_language=user.preferred_language, theme_preference=user.theme_preference,
        notification_preference=user.notification_preference, ai_preference=user.ai_preference,
    )
