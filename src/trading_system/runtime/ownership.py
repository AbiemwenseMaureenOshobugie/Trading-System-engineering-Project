"""Single-process runtime ownership for MS-0.17."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Protocol


class RuntimeOwnershipError(RuntimeError):
    """Raised when runtime ownership cannot be acquired or released."""


class RuntimeOwnership(Protocol):
    def acquire(self) -> None: ...
    def release(self) -> None: ...


class FileRuntimeOwnership:
    """OS/process-level exclusive lock for one runtime identity."""

    def __init__(self, *, runtime_id: str, lock_directory: str | os.PathLike[str]) -> None:
        if not runtime_id.strip():
            raise ValueError("runtime_id must not be blank")
        self._runtime_id = runtime_id
        self._directory = Path(lock_directory)
        digest = hashlib.sha256(runtime_id.encode("utf-8")).hexdigest()
        self._path = self._directory / f"aster-{digest}.lock"
        self._handle = None

    @property
    def path(self) -> Path:
        return self._path

    def acquire(self) -> None:
        if self._handle is not None:
            raise RuntimeOwnershipError("runtime ownership is already held")
        self._directory.mkdir(parents=True, exist_ok=True)
        handle = open(self._path, "a+b")
        try:
            handle.seek(0)
            handle.write(b"0")
            handle.flush()
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            handle.close()
            raise RuntimeOwnershipError(
                f"runtime ownership unavailable for {self._runtime_id}"
            ) from exc
        self._handle = handle

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        except OSError as exc:
            raise RuntimeOwnershipError(
                f"runtime ownership release failed for {self._runtime_id}"
            ) from exc
        finally:
            self._handle.close()
            self._handle = None
