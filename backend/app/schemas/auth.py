from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class Credentials(BaseModel):
    login: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=255)
    username: str = Field(pattern=r"^[A-Za-z0-9_.-]+$", min_length=3, max_length=80)
    password: str = Field(min_length=10, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    username: str
    created_at: datetime


class AuthOut(BaseModel):
    user: UserOut
    csrf_token: str
