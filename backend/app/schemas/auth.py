from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: str
    full_name: str
    email: str
    preferred_language: str
    theme_preference: str
    notification_preference: bool
    ai_preference: str | None


class AuthResponse(BaseModel):
    user: UserOut
    message: str = "Authenticated"


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr


class PreferenceUpdate(BaseModel):
    preferred_language: str | None = Field(default=None, pattern="^(en|ar)$")
    theme_preference: str | None = Field(default=None, pattern="^(light|system)$")
    notification_preference: bool | None = None
    ai_preference: str | None = Field(default=None, pattern="^(groq|gemini|auto)$")


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
