"""Public session contracts; ownership itself is never supplied by a client."""

from typing import Literal

from pydantic import Field, SecretStr, field_validator

from docintel.domain.models import Contract


class Credentials(Contract):
    username: str = Field(pattern=r"^[a-z][a-z0-9_-]{2,31}$")
    password: SecretStr = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def valid_password_encoding(cls, value: SecretStr) -> SecretStr:
        try:
            value.get_secret_value().encode("utf-8")
        except UnicodeError as exc:
            raise ValueError("Password contains invalid Unicode") from exc
        return value


class UserIdentity(Contract):
    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    username: str


class SessionState(Contract):
    mode: Literal["local", "session"]
    user: UserIdentity | None = None
    csrf_token: str | None = Field(default=None, repr=False)
