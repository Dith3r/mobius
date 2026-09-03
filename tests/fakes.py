import threading
from datetime import datetime
from typing import List
from uuid import UUID

from mobius.commons.locker.model import Lock
from mobius.commons.locker.repository import LocksRepository
from mobius.commons.logger.model import Log
from mobius.commons.logger.repository import LogsRepository
from mobius.commons.repositories import UniqueViolationError


def clone_log(log: Log) -> Log:
    return Log(
        id=log.id,
        created_at=log.created_at,
        updated_at=log.updated_at,
        hash=log.hash,
        state=log.state,
        msg=log.msg,
    )


class FakeLocksRepository(LocksRepository):
    def __init__(self):
        self.locks = {}
        self.mutex = threading.Lock()
        self.update_calls = 0
        self.fail_updates = False
        self.raise_on_update = False

    def ensure_indexes(self):
        pass

    def insert(self, lock: Lock):
        with self.mutex:
            if lock.id in self.locks:
                raise UniqueViolationError(str(lock.id))
            self.locks[lock.id] = lock

    def insert_many(self, locks: List[Lock]):
        for lock in locks:
            self.insert(lock)

    def update_by_transaction_id(
        self, transaction_id: UUID, valid_till: datetime
    ) -> bool:
        with self.mutex:
            self.update_calls += 1

            if self.raise_on_update:
                raise RuntimeError("connection lost")
            if self.fail_updates:
                return False

            for lock in self.locks.values():
                if lock.transaction_id == transaction_id:
                    lock.valid_till = valid_till
                    return True

            return False

    def delete_by_transaction_id(self, transaction_id: UUID):
        with self.mutex:
            self.locks = {
                key: lock
                for key, lock in self.locks.items()
                if lock.transaction_id != transaction_id
            }

    def delete_by_holder_id(self, holder_id: UUID):
        with self.mutex:
            self.locks = {
                key: lock
                for key, lock in self.locks.items()
                if lock.holder_id != holder_id
            }


class FakeLogsRepository(LogsRepository):
    def __init__(self):
        self.logs = {}

    def ensure_indexes(self):
        pass

    def fetch_by_states_limit(self, states, limit) -> List[Log]:
        rows = sorted(
            (log for log in self.logs.values() if log.state in states),
            key=lambda log: log.id,
        )

        return [clone_log(log) for log in rows[:limit]]

    def fetch_by_ids(self, migration_ids: List[int]) -> List[Log]:
        return [
            clone_log(self.logs[migration_id])
            for migration_id in migration_ids
            if migration_id in self.logs
        ]

    def update(self, log: Log) -> bool:
        if log.id not in self.logs:
            return False

        self.logs[log.id] = clone_log(log)
        return True

    def insert(self, log: Log):
        if log.id in self.logs:
            raise UniqueViolationError(str(log.id))

        self.logs[log.id] = clone_log(log)


class FakeDriverManager:
    def __init__(self):
        self.configs = {}
        self.resolved = False

    def resolve_all(self):
        self.resolved = True
