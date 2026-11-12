"""Public session contracts; ownership itself is never supplied by a client."""

from typing import Literal

from pydantic import Field, SecretStr

from docintel.domain.models import Contract


class Credentials(Contract):
    username: str = Field(pattern=r"^[a-z][a-z0-9_-]{2,31}$")
    password: SecretStr = Field(min_length=12, max_length=128)


class UserIdentity(Contract):
    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    username: str


class SessionState(Contract):
    mode: Literal["local", "session"]
    user: UserIdentity | None = None
    csrf_token: str | None = None
