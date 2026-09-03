import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from mobius.commons.locker.model import Lock, LockFailedException, LockLostException
from mobius.commons.locker.repository import LocksRepository
from mobius.commons.repositories import UniqueViolationError


logger = logging.getLogger("lock")


class ILockerDriver:
    def get_locks_repository(self) -> "LocksRepository":
        raise NotImplementedError


class LockHandle:
    __slots__ = ("transaction_id", "_lost")

    def __init__(self, transaction_id: UUID, lost: threading.Event):
        self.transaction_id = transaction_id
        self._lost = lost

    @property
    def lost(self) -> bool:
        return self._lost.is_set()

    def ensure_valid(self):
        if self.lost:
            raise LockLostException()


class Locker:
    def __init__(self, locks_repository: LocksRepository):
        self.locks_repository = locks_repository

    @contextmanager
    def lock(self, lock_id: UUID, holder_id: UUID, ttl: int) -> LockHandle:
        transaction_id = uuid4()
        transaction_time = datetime.utcnow() + timedelta(seconds=ttl)

        logger.debug(f"Locking with {transaction_id} for holder {holder_id}")

        try:
            lock = Lock(lock_id, transaction_time, transaction_id, holder_id)
            self.locks_repository.insert(lock)
        except UniqueViolationError:
            raise LockFailedException()

        logger.debug("Lock acquired.")

        stop = threading.Event()
        lost = threading.Event()

        heartbeat = threading.Thread(
            target=self._heartbeat,
            args=(transaction_id, ttl, stop, lost),
            daemon=True,
        )
        heartbeat.start()

        try:
            yield LockHandle(transaction_id, lost)
        finally:
            stop.set()
            heartbeat.join()

            self.locks_repository.delete_by_transaction_id(transaction_id)

    def ensure_index(self):
        self.locks_repository.ensure_indexes()

    def _heartbeat(
        self,
        transaction_id: UUID,
        ttl: int,
        stop: threading.Event,
        lost: threading.Event,
    ):
        next_beat = self._next_beat(ttl)
        while not stop.wait(0.1):
            if datetime.utcnow() > next_beat:
                logger.debug("Update lock TTL")

                next_beat = self._next_beat(ttl)

                try:
                    result = self.locks_repository.update_by_transaction_id(
                        transaction_id, datetime.utcnow() + timedelta(seconds=ttl)
                    )
                except Exception:
                    logger.error("Lock heartbeat failed", exc_info=True)
                    lost.set()
                    return

                if not result:
                    logger.error("Lock heartbeat failed - lock no longer held")
                    lost.set()
                    return

    def _next_beat(self, ttl):
        return datetime.utcnow() + timedelta(seconds=max(1, int(ttl / 3)))
