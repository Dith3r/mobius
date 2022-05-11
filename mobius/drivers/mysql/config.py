from typing import Optional

from mobius.drivers.manager import (
    CommonDriverMapper,
    DriverResolvedConfig,
    DriverUnresolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)


class MysqlConfigDriver(IDriverConfig):
    user: Optional[str]
    password: Optional[str]
    host: Optional[str]
    database: Optional[str]
    warning_exceptions: bool
    pure: bool

    def __init__(
        self,
        host: Optional[str],
        database: Optional[str],
        user: Optional[str],
        password: Optional[str],
        warning_exceptions: Optional[bool],
        pure: Optional[bool],
    ):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.warning_exceptions = warning_exceptions
        self.pure = pure


class MysqlResolvedConfigDriver(DriverResolvedConfig):
    def __init__(self, name: str, config: MysqlConfigDriver):
        super().__init__(name, config)

    def initialize(self):
        pass


class MySqlConfigDriverMapper(IConfigDriverMapper):
    JSON_KIND = "MYSQL"
    KIND = MysqlConfigDriver

    class DEFAULT:
        __slots__ = ()

    class FIELDS(CommonDriverMapper.Fields):
        __slots__ = ()
        USER = "user"
        PASSWORD = "password"
        HOST = "host"
        DATABASE = "database"
        WARNING_EXCEPTIONS = "warningExceptions"
        PURE = "pure"

    @classmethod
    def from_json(cls, name: str, data: dict) -> IDriverConfig:
        _ = cls.FIELDS

        resolver = data[_.RESOLVER]
        config = data.get(_.CONFIG, {})
        properties = data.get(_.PROPERTIES, {})

        if not isinstance(config, dict):
            raise RuntimeError("Invalid config for driver %s", name)

        if not isinstance(properties, dict):
            raise RuntimeError("Invalid properties for driver %s, name")

        user = config.get(_.USER)
        password = config.get(_.PASSWORD)
        host = config.get(_.HOST)
        database = config.get(_.DATABASE)
        warning_exceptions = config.get(_.WARNING_EXCEPTIONS)
        pure = config.get(_.PURE)

        if resolver:
            return DriverUnresolvedConfig(name, resolver, config, properties)
        else:
            return DriverResolvedConfig(
                name,
                MysqlConfigDriver(
                    host, database, user, password, warning_exceptions, pure
                ),
            )
