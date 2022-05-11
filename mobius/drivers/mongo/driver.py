from typing import Any

from pymongo import MongoClient

from mobius.commons.driver import IDriver
from mobius.commons.locker.service import ILockerDriver
from mobius.commons.logger.service import IStateDriver
from mobius.drivers.mongo.locker import LocksMongoRepository
from mobius.drivers.mongo.logger import LogsMongoRepository


class MongoDriver(IDriver, IStateDriver, ILockerDriver):
    def connection(self) -> Any:
        return self.client

    def close(self, connection: Any):
        self.client.close()

    def get_logs_repository(self):
        return LogsMongoRepository(self.client)

    def get_locks_repository(self) -> LocksMongoRepository:
        return LocksMongoRepository(self.client)

    def __init__(self, name: str, mongo_client: MongoClient):
        self.name = name
        self.client = mongo_client

    def __str__(self):
        return f"{self.__class__.__name__}[name=`{self.name}`, database=`{self.client.get_default_database()}`]"
