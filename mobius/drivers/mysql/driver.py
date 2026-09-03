from typing import TYPE_CHECKING, Any

import pymysql

from mobius.commons.driver import IDriver
from mobius.commons.locker.service import ILockerDriver
from mobius.commons.logger.service import IStateDriver
from mobius.drivers.mysql.locker import LocksMySqlRepository
from mobius.drivers.mysql.logger import LogsMySqlRepository


if TYPE_CHECKING:
    from mobius.drivers.mysql.config import MysqlConfigDriver


class MySqlDriver(IDriver, IStateDriver, ILockerDriver):
    def __init__(self, name: str, config: "MysqlConfigDriver"):
        self.name = name
        self.config = config

    def connection(self) -> Any:
        return self._connect(autocommit=False)

    def close(self, connection: Any):
        connection.close()

    def get_logs_repository(self) -> LogsMySqlRepository:
        return LogsMySqlRepository(self._repository_connection())

    def get_locks_repository(self) -> LocksMySqlRepository:
        return LocksMySqlRepository(self._repository_connection())

    def _repository_connection(self):
        # dedicated connection per repository: the lock heartbeat thread and the
        # main thread must never share one connection
        return self._connect(autocommit=True)

    def _connect(self, autocommit: bool):
        return pymysql.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.user,
            password=self.config.password,
            connect_timeout=self.config.connect_timeout,
            autocommit=autocommit,
        )

    def __str__(self):
        return f"{self.__class__.__name__}[name=`{self.name}`]"
