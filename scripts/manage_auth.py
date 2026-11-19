"""Offline account/migration administration. Never accept passwords via argv or print secrets."""

import argparse
import getpass
import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from backup_runtime import backup
from docintel.domain.auth import Credentials
from docintel.repositories.identity import IdentityRepository
from docintel.repositories.locking import RuntimeLock
from docintel.repositories.schema import upgrade_connection, version
from docintel.repositories.sqlite import DocumentRepository
from docintel.security import hash_password


@contextmanager
def offline_runtime(runtime: Path):
    locks = [RuntimeLock(runtime / "app.lock"), RuntimeLock(runtime / "worker.lock")]
    try:
        for lock in locks:
            lock.acquire()
        yield
    finally:
        for lock in reversed(locks):
            lock.release()


def manage_user(
    runtime: Path, action: str, username: str | None = None, password: str | None = None
):
    with offline_runtime(runtime):
        repository = DocumentRepository(runtime / "documents.sqlite3")
        repository.initialize()
        identities = IdentityRepository(repository)
        if action == "list-users":
            with repository.transaction() as connection:
                return [
                    dict(row)
                    for row in connection.execute(
                        "SELECT user_id,username,is_active FROM users WHERE user_id!='local' ORDER BY username"
                    )
                ]
        if action in {"create-user", "reset-password"}:
            credentials = Credentials(username=username, password=password)
            encoded = hash_password(credentials.password.get_secret_value())
            if action == "create-user":
                identities.create_user(credentials.username, encoded)
                return
        row = identities.user(username or "")
        if row is None or row["user_id"] == "local":
            raise ValueError("Account not found")
        if action == "disable-user":
            identities.disable(row["user_id"])
        elif action == "reset-password":
            identities.reset_password(row["user_id"], encoded)
        else:
            raise ValueError("Unsupported administration command")


def migrate_runtime(runtime: Path, destination: Path):
    if destination.resolve().is_relative_to(runtime.resolve()):
        raise ValueError("Backup must be outside runtime")
    database = runtime / "documents.sqlite3"
    if not database.is_file():
        raise ValueError("Existing runtime required")
    with offline_runtime(runtime), closing(sqlite3.connect(database)) as connection:
        if version(connection) != 1:
            raise RuntimeError("Expected schema 1; no migration performed")
        backup(runtime, destination)
        upgrade_connection(connection)


def adopt_local(runtime: Path, username: str, destination: Path):
    if destination.resolve().is_relative_to(runtime.resolve()):
        raise ValueError("Backup must be outside runtime")
    with offline_runtime(runtime):
        repository = DocumentRepository(runtime / "documents.sqlite3")
        repository.initialize()
        user = IdentityRepository(repository).user(username)
        if user is None or user["user_id"] == "local" or not user["is_active"]:
            raise ValueError("An active target identity is required")
        backup(runtime, destination)
        with repository.transaction(write=True) as connection:
            connection.execute(
                "UPDATE documents SET owner_id=? WHERE owner_id='local'",
                (user["user_id"],),
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    migrate = commands.add_parser("migrate")
    migrate.add_argument("--backup", type=Path, required=True)
    adopt = commands.add_parser("adopt-local")
    adopt.add_argument("--owner", required=True)
    adopt.add_argument("--backup", type=Path, required=True)
    adopt.add_argument("--confirm", action="store_true", required=True)
    commands.add_parser("list-users")
    for action in ("create-user", "disable-user", "reset-password"):
        command = commands.add_parser(action)
        command.add_argument("username")
    args = parser.parse_args()
    if args.command == "migrate":
        migrate_runtime(args.runtime, args.backup)
        print("Migration verified; previous runtime preserved in backup.")
    elif args.command == "adopt-local":
        adopt_local(args.runtime, args.owner, args.backup)
        print("Local documents assigned after backup; source files unchanged.")
    else:
        password = None
        if args.command in {"create-user", "reset-password"}:
            password = getpass.getpass("Password (12–128 characters): ")
            if password != getpass.getpass("Repeat password: "):
                raise SystemExit("Passwords do not match; nothing changed.")
        result = manage_user(
            args.runtime, args.command, getattr(args, "username", None), password
        )
        print(
            json.dumps(result)
            if result is not None
            else "Identity administration completed."
        )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, sqlite3.Error):
        raise SystemExit(
            "Administration failed; check runtime state, input and backup destination. No secrets are reported."
        ) from None
