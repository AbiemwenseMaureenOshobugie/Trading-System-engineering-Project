"""MS-0.18 single owned runtime scheduler."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Event, Thread
from typing import Callable, Sequence


class RuntimeScheduler:
    """Wait for operational boundaries and invoke RuntimeControl sequentially."""

    VERSION = "MS-0.18"

    def __init__(
        self,
        *,
        instruments: Sequence[str],
        next_invocation_at: Callable[[str, datetime], datetime | None],
        run_if_due: Callable[[str, datetime], object],
        clock: Callable[[], datetime],
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._instruments = tuple(instruments)
        self._next_invocation_at = next_invocation_at
        self._run_if_due = run_if_due
        self._clock = clock
        self._sleep = sleep
        self._stop = Event()
        self._thread: Thread | None = None
        self._last_invocation: dict[str, datetime] = {}

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            raise RuntimeError("runtime scheduler is already running")
        self._stop.clear()
        self._thread = Thread(
            target=self._run,
            name="aster-runtime-scheduler",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join()
        self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            now = self._utc(self._clock())
            due: list[tuple[str, datetime]] = []
            future: list[datetime] = []

            for instrument in self._instruments:
                scheduled = self._next_invocation_at(instrument, now)
                if scheduled is None:
                    continue
                scheduled = self._utc(scheduled)
                last = self._last_invocation.get(instrument)

                if scheduled <= now:
                    if last != scheduled:
                        due.append((instrument, scheduled))
                else:
                    future.append(scheduled)

            if due:
                for instrument, scheduled in due:
                    if self._stop.is_set():
                        return
                    try:
                        self._run_if_due(instrument, self._utc(self._clock()))
                    except Exception:
                        # RuntimeControl owns failure visibility. The scheduler
                        # isolates this instrument and continues with the next.
                        pass
                    finally:
                        self._last_invocation[instrument] = scheduled
                continue

            if future:
                wait_seconds = max(
                    0.0, (min(future) - self._utc(self._clock())).total_seconds()
                )
                self._wait(wait_seconds)
            else:
                # The boundary authority is responsible for producing the next
                # operational boundary. The scheduler invents no polling interval.
                self._stop.wait()

    def _wait(self, seconds: float) -> None:
        if self._sleep is not None:
            self._sleep(seconds)
        else:
            self._stop.wait(seconds)

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("scheduler timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)
