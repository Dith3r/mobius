from typing import Any, Dict, Optional

from mobius.drivers.manager import (
    CommonDriverMapper,
    DriverResolvedConfig,
    DriverUnresolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)
from mobius.drivers.mysql.driver import MySqlDriver


class MysqlConfigDriver(IDriverConfig):
    host: Optional[str]
    port: int
    database: Optional[str]
    user: Optional[str]
    password: Optional[str]
    connect_timeout: int

    def __init__(
        self,
        host: Optional[str],
        port: int,
        database: Optional[str],
        user: Optional[str],
        password: Optional[str],
        connect_timeout: int,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connect_timeout = connect_timeout

    def __str__(self):
        return (
            f"{self.__class__.__name__}[host={self.host}, port={self.port}, "
            f"database={self.database}, user={self.user}]"
        )


class MysqlResolvedConfigDriver(DriverResolvedConfig):
    config: MysqlConfigDriver

    def __init__(self, name: str, config: MysqlConfigDriver):
        super().__init__(name, config)

    def initialize(self) -> MySqlDriver:
        return MySqlDriver(self.name, self.config)

    def __str__(self):
        return f"{self.__class__.__name__}[name={self.name},config={self.config}]"


class MysqlUnresolvedConfigDriver(DriverUnresolvedConfig):
    config: MysqlConfigDriver

    def __init__(
        self,
        name: str,
        resolver: str,
        config: MysqlConfigDriver,
        properties: Dict[str, str],
    ):
        super().__init__(name, resolver, config, properties)

    def resolve(self, resolved_properties: Dict[str, Any]) -> DriverResolvedConfig:
        def interpolate(value: Optional[str]) -> Optional[str]:
            if value is None:
                return None
            return value % resolved_properties

        mysql_config = MysqlConfigDriver(
            host=interpolate(self.config.host),
            port=int(str(self.config.port) % resolved_properties),
            database=interpolate(self.config.database),
            user=interpolate(self.config.user),
            password=interpolate(self.config.password),
            connect_timeout=self.config.connect_timeout,
        )

        return MysqlResolvedConfigDriver(self.name, mysql_config)


class MySqlConfigDriverMapper(IConfigDriverMapper):
    __slots__ = ()
    JSON_KIND = "MYSQL"
    KIND = MysqlConfigDriver

    class DEFAULT:
        __slots__ = ()
        PORT = 3306
        CONNECT_TIMEOUT = 10

    class FIELDS(CommonDriverMapper.Fields):
        __slots__ = ()
        USER = "user"
        PASSWORD = "password"
        HOST = "host"
        PORT = "port"
        DATABASE = "database"
        CONNECT_TIMEOUT = "connectTimeout"

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

        mysql_config = MysqlConfigDriver(
            host=config.get(_.HOST),
            port=config.get(_.PORT, cls.DEFAULT.PORT),
            database=config.get(_.DATABASE),
            user=config.get(_.USER),
            password=config.get(_.PASSWORD),
            connect_timeout=int(
                config.get(_.CONNECT_TIMEOUT, cls.DEFAULT.CONNECT_TIMEOUT)
            ),
        )

        if resolver:
            return MysqlUnresolvedConfigDriver(name, resolver, mysql_config, properties)
        else:
            return MysqlResolvedConfigDriver(name, mysql_config)
