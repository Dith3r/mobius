from __future__ import annotations

from typing import Any, Dict

from mobius.commons.mapping import InvalidValueError, ObjectContext
from mobius.drivers.manager import (
    CommonDriverMapper,
    DriverResolvedConfig,
    DriverUnresolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)
from mobius.drivers.mysql.driver import MySqlDriver


class MysqlConfigDriver(IDriverConfig):
    host: str | None
    port: int
    database: str | None
    user: str | None
    password: str | None
    connect_timeout: int

    def __init__(
        self,
        host: str | None,
        port: int,
        database: str | None,
        user: str | None,
        password: str | None,
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
        def interpolate(value: str | None) -> str | None:
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
    def from_context(
        cls, name: str, context: ObjectContext
    ) -> IDriverConfig | None:
        _ = cls.FIELDS

        resolver = context.find_string(_.RESOLVER).or_none()
        properties = context.find_string_map(_.PROPERTIES).or_else({})

        def read_config(config: ObjectContext) -> MysqlConfigDriver | None:
            host = config.get_string(_.HOST)
            port = config.find_int(_.PORT).or_else(cls.DEFAULT.PORT)
            database = config.find_string(_.DATABASE).or_none()
            user = config.find_string(_.USER).or_none()
            password = config.find_string(_.PASSWORD).or_none()
            connect_timeout = (
                config.find_int(_.CONNECT_TIMEOUT)
                .must(
                    InvalidValueError(reason="must be positive"),
                    lambda value: value > 0,
                )
                .or_else(cls.DEFAULT.CONNECT_TIMEOUT)
            )

            return config.construct(
                lambda: MysqlConfigDriver(
                    host.require(), port, database, user, password, connect_timeout
                )
            )

        mysql_config = context.get_object(_.CONFIG, read_config).or_none()
        if mysql_config is None:
            return None

        if resolver:
            return MysqlUnresolvedConfigDriver(name, resolver, mysql_config, properties)

        return MysqlResolvedConfigDriver(name, mysql_config)
