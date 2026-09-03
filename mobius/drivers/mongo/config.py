from __future__ import annotations

from typing import Any, Dict
from urllib.parse import quote_plus

from pymongo import MongoClient

from mobius.commons.mapping import InvalidValueError, ObjectContext
from mobius.drivers.manager import (
    CommonDriverMapper,
    DriverResolvedConfig,
    DriverUnresolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)
from mobius.drivers.mongo.driver import MongoDriver


class MongoConfigDriver(IDriverConfig):
    connection_url: str | None
    uuid: str
    max_pool: int

    def __init__(
        self, connection_url: str | None, uuid: str, max_pool: int | None
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
    def from_context(
        cls, name: str, context: ObjectContext
    ) -> IDriverConfig | None:
        _ = cls.FIELDS

        resolver = context.find_string(_.RESOLVER).or_none()
        properties = context.find_string_map(_.PROPERTIES).or_else({})

        def read_config(config: ObjectContext) -> MongoConfigDriver | None:
            connection_url = config.get_string(_.CONNECTION_URL)
            uuid = config.find_string(_.UUID).or_else(cls.DEFAULT.UUID)
            max_pool_size = (
                config.find_int(_.MAX_POOL_SIZE)
                .must(
                    InvalidValueError(reason="must be positive"),
                    lambda value: value > 0,
                )
                .or_else(cls.DEFAULT.MAX_POOL_SIZE)
            )

            return config.construct(
                lambda: MongoConfigDriver(
                    connection_url.require(), uuid, max_pool_size
                )
            )

        mongo_config = context.get_object(_.CONFIG, read_config).or_none()
        if mongo_config is None:
            return None

        if resolver:
            return MongoUnresolvedConfigDriver(name, resolver, mongo_config, properties)

        return MongoResolvedConfigDriver(name, mongo_config)
