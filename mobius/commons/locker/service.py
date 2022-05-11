import logging
import sys
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from time import sleep
from typing import Callable
from uuid import UUID, uuid4

from mobius.commons.locker.model import Lock, LockFailedException
from mobius.commons.locker.repository import LocksRepository
from mobius.commons.repositories import UniqueViolationError


logger = logging.getLogger("lock")


class ILockerDriver:
    def get_locks_repository(self) -> "LocksRepository":
        raise NotImplementedError


class Locker:
    def __init__(self, locks_repository: LocksRepository):
        self.locks_repository = locks_repository

    @contextmanager
    def lock(self, lock_id: UUID, holder_id: UUID, ttl: int) -> UUID:
        transaction_id = uuid4()
        transaction_time = datetime.utcnow() + timedelta(seconds=ttl)
        heartbeat = None
        stop_heartbeat = False

        logger.debug(f"Locking with {transaction_id} for holder {holder_id}")

        try:
            lock = Lock(lock_id, transaction_time, transaction_id, holder_id)
            self.locks_repository.insert(lock)
            logger.debug("Lock acquired.")

            heartbeat = threading.Thread(
                target=self._heartbeat,
                args=[transaction_id, ttl, lambda: stop_heartbeat],
            )
            heartbeat.start()

            yield transaction_id

        except UniqueViolationError:
            raise LockFailedException()
        finally:
            if heartbeat and heartbeat.is_alive():
                stop_heartbeat = True
                heartbeat.join()

            self.locks_repository.delete_by_transaction_id(transaction_id)

    def ensure_index(self):
        self.locks_repository.ensure_indexes()

    def _heartbeat(self, transaction_id: UUID, ttl, stop: Callable):
        next_beat = self._next_beat(ttl)
        while not stop():
            if datetime.utcnow() > next_beat:
                logger.debug("Update lock TTL")

                next_beat = self._next_beat(ttl)

                result = self.locks_repository.update_by_transaction_id(
                    transaction_id, datetime.utcnow() + timedelta(seconds=ttl)
                )
                if not result:
                    print("LOCK HEARTBEAT FAILED!")
                    sys.exit(-1)
            sleep(0.1)

    def _next_beat(self, ttl):
        return datetime.utcnow() + timedelta(seconds=max(1, int(ttl / 3)))
