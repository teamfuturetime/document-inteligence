"""Private same-filesystem staging and atomic directory publication without replacement."""

import ctypes
import errno
import logging
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


def new_destination(destination: Path) -> Path:
    # Requested leaf semantics include a dangling symlink or Windows junction.
    try:
        destination.lstat()
    except FileNotFoundError:
        return destination.resolve()
    raise FileExistsError("Destination already exists")


@contextmanager
def staging_directory(destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    owned = Path(tempfile.mkdtemp(prefix=".docintel-staging-", dir=destination.parent))
    try:
        yield owned / "payload"
    finally:
        try:
            shutil.rmtree(owned)
        except OSError:
            # Preserve original errors and never remove destination or source. An
            # empty token dir can also remain after successful publication/cleanup failure.
            logger.warning("Task-owned staging retained: cleanup requires offline inspection")


def sync_files(directory: Path):
    for path in directory.rglob("*"):
        if path.is_file():
            with path.open("r+b") as stream:
                stream.flush()
                os.fsync(stream.fileno())


def publish_directory(source: Path, destination: Path):
    """No check-then-overwriting rename fallback, even for empty destination directories."""
    if os.name == "nt":
        os.rename(source, destination)  # Windows rename refuses every existing destination.
        return
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        if sys.platform == "darwin":
            rename = libc.renamex_np
            rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
            arguments = (os.fsencode(source), os.fsencode(destination), 0x4)  # RENAME_EXCL
        elif sys.platform.startswith("linux"):
            rename = libc.renameat2
            rename.argtypes = [
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            ]
            arguments = (
                -100,
                os.fsencode(source),
                -100,
                os.fsencode(destination),
                1,
            )  # AT_FDCWD/NOREPLACE
        else:
            raise OSError(errno.ENOTSUP, "Exclusive directory publication is unsupported")
    except AttributeError:
        raise OSError(errno.ENOTSUP, "Exclusive directory publication is unsupported") from None
    rename.restype = ctypes.c_int
    if rename(*arguments) != 0:
        raise OSError(ctypes.get_errno(), "Exclusive directory publication failed")
