from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from pymongo import MongoClient

from mobius.drivers.manager import (
    CommonDriverMapper,
    DriverResolvedConfig,
    DriverUnresolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)
from mobius.drivers.mongo.driver import MongoDriver


class MongoConfigDriver(IDriverConfig):
    connection_url: Optional[str]
    uuid: str
    max_pool: int

    def __init__(
        self, connection_url: Optional[str], uuid: str, max_pool: Optional[int]
    ):
        self.connection_url = connection_url
        self.uuid = uuid
        self.max_pool = max_pool

    def __str__(self):
        return f"{self.__class__.__name__}[connection_url={self.connection_url}, uuid={self.uuid}, max_pool={self.max_pool}]"


class MongoResolvedConfigDriver(DriverResolvedConfig):
    config: MongoConfigDriver

    def __init__(self, name: str, config: MongoConfigDriver):
        super().__init__(name, config)

    def initialize(self) -> MongoDriver:
        return MongoDriver(
            self.name,
            MongoClient(
                self.config.connection_url,
                uuidRepresentation=self.config.uuid,
                maxPoolSize=self.config.max_pool,
            ),
        )

    def __str__(self):
        return f"{self.__class__.__name__}[name={self.name},config={self.config}]"


class MongoUnresolvedConfigDriver(DriverUnresolvedConfig):
    config: MongoConfigDriver

    def __init__(
        self,
        name: str,
        resolver: str,
        config: MongoConfigDriver,
        properties: Dict[str, str],
    ):
        super().__init__(name, resolver, config, properties)

    def resolve(self, resolved_properties: Dict[str, Any]) -> DriverResolvedConfig:
        quoted = {
            key: quote_plus(str(value)) for key, value in resolved_properties.items()
        }

        mongo_config = MongoConfigDriver(
            self.config.connection_url % quoted,
            uuid=self.config.uuid % resolved_properties,
            max_pool=int(str(self.config.max_pool) % resolved_properties),
        )

        return MongoResolvedConfigDriver(self.name, mongo_config)


class MongoConfigDriverMapper(IConfigDriverMapper):
    __slots__ = ()
    JSON_KIND = "MONGO"
    KIND = MongoConfigDriver

    class DEFAULT:
        __slots__ = ()
        UUID = "standard"
        MAX_POOL_SIZE = 10

    class FIELDS(CommonDriverMapper.Fields):
        __slots__ = ()
        UUID = "uuid"
        MAX_POOL_SIZE = "maxPoolSize"
        CONNECTION_URL = "connectionUrl"

    @classmethod
    def from_json(cls, name: str, data: dict) -> IDriverConfig:
        _ = cls.FIELDS

        resolver = data[_.RESOLVER]
        config = data.get(_.CONFIG, {})
        properties = data.get(_.PROPERTIES, {})

        if not isinstance(config, dict):
            raise RuntimeError("Invalid config for driver %s", name)

        if not isinstance(properties, dict):
            raise RuntimeError("Invalid properties for driver %s", name)

        connection_url = config.get(_.CONNECTION_URL)
        uuid = config.get(_.UUID, cls.DEFAULT.UUID)
        max_pool_size = int(config.get(_.MAX_POOL_SIZE, cls.DEFAULT.MAX_POOL_SIZE))

        if resolver:
            return MongoUnresolvedConfigDriver(
                name,
                resolver,
                MongoConfigDriver(connection_url, uuid, max_pool_size),
                properties,
            )
        else:
            return MongoResolvedConfigDriver(
                name, MongoConfigDriver(connection_url, uuid, max_pool_size)
            )
