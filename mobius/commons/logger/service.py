from datetime import datetime
from typing import List

from mobius.commons.command import CommandException
from mobius.commons.logger.model import Failed, InProgress, Log
from mobius.commons.logger.repository import LogsRepository


class NotCompletedMigrationsFoundException(CommandException):
    __slots__ = ("log",)

    def __init__(self, log: Log):
        self.log = log
        super().__init__("MIGRATION.NOT_COMPLETED_FOUND")


class IStateDriver:
    __slots__ = ()

    def get_logs_repository(self):
        raise NotImplementedError


class Logger:
    def __init__(self, logs_repository: LogsRepository):
        self.logs_repository = logs_repository

    def ensure_index(self):
        self.logs_repository.ensure_indexes()

    def ensure_all_completed(self):
        failed_migrations = self.logs_repository.fetch_by_states_limit(
            states=[Failed, InProgress], limit=1
        )

        if failed_migrations:
            raise NotCompletedMigrationsFoundException(failed_migrations.pop())

    def fetch_by_id(self, migration_ids: List[int]) -> List[Log]:
        return self.logs_repository.fetch_by_ids(migration_ids)

    def update(self, log: Log):
        log.updated_at = datetime.utcnow()
        self.logs_repository.update(log)

    def insert(self, log: Log):
        self.logs_repository.insert(log)
