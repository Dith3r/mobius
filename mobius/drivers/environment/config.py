from typing import Any, Dict, Optional

from mobius.drivers.environment.diver import EnvironmentDriver
from mobius.drivers.manager import (
    CommonDriverMapper,
    DriverResolvedConfig,
    DriverUnresolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)


class EnvironmentConfigDriver(IDriverConfig):
    prefix: Optional[str]
    sufix: Optional[str]
    separator: str

    def __init__(self, prefix: Optional[str], sufix: Optional[str], separator="_"):
        self.prefix = prefix
        self.sufix = sufix
        self.separator = separator

    def __str__(self):
        return f"{self.__class__.__name__}[prefix={self.prefix}, sufix={self.sufix}, separator={self.separator}]"

    def __repr__(self):
        return self.__str__()


class EnvironmentUnresolvedConfigDriver(DriverUnresolvedConfig):
    config: EnvironmentConfigDriver

    def resolve(self, config: Dict[str, Any]) -> DriverResolvedConfig:
        return EnvironmentResolvedConfigDriver(
            self.name,
            config=EnvironmentConfigDriver(
                self.config.prefix % config if self.config.prefix else None,
                self.config.sufix % config if self.config.sufix else None,
            ),
        )


class EnvironmentResolvedConfigDriver(DriverResolvedConfig):
    config: EnvironmentConfigDriver

    def __init__(self, name: str, config: EnvironmentConfigDriver):
        super().__init__(name, config)

    def initialize(self):
        return EnvironmentDriver(self)

    def __str__(self):
        return f"{self.__class__.__name__}[name={self.name}, config={self.config}]"


class EnvironmentConfigDriverMapper(IConfigDriverMapper):
    JSON_KIND = "ENV"
    KIND = EnvironmentConfigDriver

    class DEFAULT:
        __slots__ = ()
        PREFIX = ""
        SUFIX = ""

    class FIELDS(CommonDriverMapper.Fields):
        __slots__ = ()
        PREFIX = "prefix"
        SUFIX = "sufix"

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

        prefix = config.get(_.PREFIX)
        if prefix is None:
            prefix = cls.DEFAULT.PREFIX
        else:
            prefix = str(prefix)

        sufix = config.get(_.SUFIX)
        if sufix is None:
            sufix = cls.DEFAULT.SUFIX
        else:
            sufix = str(sufix)

        if resolver:
            return EnvironmentUnresolvedConfigDriver(
                name, resolver, EnvironmentConfigDriver(prefix, sufix), properties
            )
        else:
            return EnvironmentResolvedConfigDriver(
                name, EnvironmentConfigDriver(prefix, sufix)
            )
