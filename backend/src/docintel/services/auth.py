"""Opaque cookie sessions backed by SQLite; authentication never trusts client owner claims."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from docintel.config import Settings
from docintel.domain.auth import Credentials, UserIdentity
from docintel.repositories.identity import IdentityRepository
from docintel.repositories.sqlite import DocumentRepository
from docintel.security import new_token, token_digest, verify_password
from docintel.services.documents import ProductError

# Not an account or default credential; unknown users still incur the pinned KDF cost.
DUMMY_HASH = (
    "pbkdf2_sha256$600000$AAAAAAAAAAAAAAAAAAAAAA==$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
)


@dataclass(frozen=True)
class Principal:
    user: UserIdentity
    csrf_token: str = field(repr=False)
    token_hash: str = field(repr=False)
    expires_at: float


class AuthService:
    def __init__(
        self,
        settings: Settings,
        repository: DocumentRepository,
        clock: Callable[[], float] = time.time,
    ):
        self.settings = settings
        self.identities = IdentityRepository(repository)
        self.clock = clock

    def session(self, raw_token: str | None) -> Principal | None:
        digest = token_digest(raw_token or "")
        if digest is None:
            return None
        row = self.identities.active_session(digest, self.clock())
        if row is None:
            return None
        return Principal(
            UserIdentity(id=row["user_id"], username=row["username"]),
            row["csrf_token"],
            digest,
            row["expires_at"],
        )

    def login(
        self, credentials: Credentials, previous_token: str | None = None
    ) -> tuple[str, Principal]:
        if self.settings.auth_mode != "session":
            raise ProductError(404, "AUTH_DISABLED", "Chế độ tài khoản chưa được bật.")
        if not self.identities.allow_login(
            self.clock(), self.settings.max_login_attempts, self.settings.login_window_seconds
        ):
            raise ProductError(
                429,
                "LOGIN_BUSY",
                "Quá số lần đăng nhập. Vui lòng thử lại sau.",
                headers={"Retry-After": str(self.settings.login_window_seconds)},
            )
        row = self.identities.user(credentials.username)
        encoded = row["password_hash"] if row else DUMMY_HASH
        verified = verify_password(credentials.password.get_secret_value(), encoded)
        if not verified or row is None or not row["is_active"]:
            raise ProductError(401, "INVALID_CREDENTIALS", "Thông tin đăng nhập không hợp lệ.")
        raw, csrf = new_token(), new_token()
        created = self.clock()
        expires = created + self.settings.session_ttl_seconds
        try:
            self.identities.create_session(
                token_digest(raw),
                row["user_id"],
                csrf,
                created,
                expires,
                previous_hash=token_digest(previous_token or ""),
            )
        except ValueError as exc:
            raise ProductError(
                401, "INVALID_CREDENTIALS", "Thông tin đăng nhập không hợp lệ."
            ) from exc
        principal = self.session(raw)
        if principal is None:
            raise ProductError(401, "INVALID_CREDENTIALS", "Thông tin đăng nhập không hợp lệ.")
        return raw, principal

    def logout(self, raw_token: str | None):
        digest = token_digest(raw_token or "")
        if digest:
            self.identities.revoke(digest)
