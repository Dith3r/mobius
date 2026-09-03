from typing import Any

import psycopg

from mobius.commons.driver import IDriver
from mobius.commons.locker.service import ILockerDriver
from mobius.commons.logger.service import IStateDriver
from mobius.drivers.postgres.locker import LocksPostgresRepository
from mobius.drivers.postgres.logger import LogsPostgresRepository


class PostgresDriver(IDriver, IStateDriver, ILockerDriver):
    def __init__(
        self, name: str, connection_url: str, connect_timeout: int, autocommit: bool
    ):
        self.name = name
        self.connection_url = connection_url
        self.connect_timeout = connect_timeout
        self.autocommit = autocommit

    def connection(self) -> Any:
        return psycopg.connect(
            self.connection_url,
            connect_timeout=self.connect_timeout,
            autocommit=self.autocommit,
        )

    def close(self, connection: Any):
        connection.close()

    def get_logs_repository(self) -> LogsPostgresRepository:
        return LogsPostgresRepository(self._repository_connection())

    def get_locks_repository(self) -> LocksPostgresRepository:
        return LocksPostgresRepository(self._repository_connection())

    def _repository_connection(self) -> psycopg.Connection:
        # dedicated connection per repository: the lock heartbeat thread and the
        # main thread must never share one psycopg connection
        return psycopg.connect(
            self.connection_url,
            connect_timeout=self.connect_timeout,
            autocommit=True,
        )

    def __str__(self):
        return f"{self.__class__.__name__}[name=`{self.name}`]"
