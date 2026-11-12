"""SQL identity/session persistence. No raw password or session token is stored."""

import re
from uuid import uuid4

from docintel.repositories.sqlite import DocumentRepository, now


class IdentityRepository:
    def __init__(self, repository: DocumentRepository):
        self.repository = repository

    def allow_login(self, timestamp: float, maximum: int, window: int) -> bool:
        # One bounded row, never a dictionary/table keyed by attacker-controlled usernames.
        with self.repository.transaction(write=True) as connection:
            row = connection.execute(
                "SELECT window_start,attempts FROM login_budget WHERE id=1"
            ).fetchone()
            if row is None or timestamp >= row["window_start"] + window:
                connection.execute(
                    "INSERT OR REPLACE INTO login_budget VALUES(1,?,1)", (timestamp,)
                )
                return True
            if row["attempts"] >= maximum:
                return False
            connection.execute("UPDATE login_budget SET attempts=attempts+1 WHERE id=1")
            return True

    def create_user(self, username: str, password_hash: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9_-]{2,31}", username):
            raise ValueError("Invalid canonical username")
        user_id = uuid4().hex
        with self.repository.transaction(write=True) as connection:
            connection.execute(
                "INSERT INTO users VALUES(?,?,?,1,?)", (user_id, username, password_hash, now())
            )
        return user_id

    def user(self, username: str):
        with self.repository.transaction() as connection:
            return connection.execute(
                "SELECT * FROM users WHERE username=?", (username,)
            ).fetchone()

    def create_session(
        self, token_hash: str, user_id: str, csrf_token: str, created: float, expires: float
    ):
        with self.repository.transaction(write=True) as connection:
            cursor = connection.execute(
                "INSERT INTO sessions SELECT ?,?,?,?,? WHERE EXISTS("
                "SELECT 1 FROM users WHERE user_id=? AND is_active=1)",
                (token_hash, user_id, csrf_token, expires, created, user_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Inactive or missing identity")
            connection.execute("DELETE FROM sessions WHERE expires_at<=?", (created,))
            connection.execute(
                "DELETE FROM sessions WHERE user_id=? AND token_hash NOT IN ("
                "SELECT token_hash FROM sessions WHERE user_id=? "
                "ORDER BY created_at DESC,rowid DESC LIMIT 5)",
                (user_id, user_id),
            )

    def active_session(self, token_hash: str, timestamp: float):
        with self.repository.transaction() as connection:
            return connection.execute(
                "SELECT u.user_id,u.username,s.csrf_token,s.expires_at FROM sessions s "
                "JOIN users u ON u.user_id=s.user_id WHERE s.token_hash=? AND s.expires_at>? "
                "AND u.is_active=1",
                (token_hash, timestamp),
            ).fetchone()

    def revoke(self, token_hash: str):
        with self.repository.transaction(write=True) as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))

    def disable(self, user_id: str):
        with self.repository.transaction(write=True) as connection:
            connection.execute("UPDATE users SET is_active=0 WHERE user_id=?", (user_id,))
            connection.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))

    def reset_password(self, user_id: str, password_hash: str):
        with self.repository.transaction(write=True) as connection:
            connection.execute(
                "UPDATE users SET password_hash=? WHERE user_id=? AND user_id!='local'",
                (password_hash, user_id),
            )
            connection.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
