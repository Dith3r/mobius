from typing import (
    Optional,
)

from mobius.drivers.manager import (
    CommonDriverMapper,
    DriverResolvedConfig,
    DriverUnresolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)


class MongoConfigDriver(IDriverConfig):
    connection_url: Optional[str]
    uuid: str
    max_pool: int

    def __init__(self,
                 connection_url: Optional[str],
                 uuid: str,
                 max_pool: Optional[int]):
        self.connection_url = connection_url
        self.uuid = uuid
        self.max_pool = max_pool


class MongoResolvedConfigDriver(DriverResolvedConfig):
    def __init__(self,
                 name: str,
                 config: MongoConfigDriver):
        super().__init__(name, config)

    def initialize(self):
        pass


class MongoConfigDriverMapper(IConfigDriverMapper):
    __slots__ = ()
    JSON_KIND = "MONGO"
    KIND = MongoConfigDriver

    class DEFAULT:
        __slots__ = ()
        UUID = 'standard'
        MAX_POOL_SIZE = 10

    class FIELDS(CommonDriverMapper.Fields):
        __slots__ = ()
        UUID = "uuid"
        MAX_POOL_SIZE = 'maxPoolSize'
        CONNECTION_URL = 'connectionUrl'

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
            return DriverUnresolvedConfig(name,
                                          resolver,
                                          config,
                                          properties)
        else:
            return MongoResolvedConfigDriver(name,
                                             MongoConfigDriver(
                                                     connection_url,
                                                     uuid,
                                                     max_pool_size)
                                             )
