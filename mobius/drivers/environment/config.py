from __future__ import annotations

from typing import Any, Dict

from mobius.commons.mapping import ObjectContext
from mobius.drivers.environment.diver import EnvironmentDriver
from mobius.drivers.manager import (
    CommonDriverMapper,
    DriverResolvedConfig,
    DriverUnresolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)


class EnvironmentConfigDriver(IDriverConfig):
    prefix: str | None
    sufix: str | None
    separator: str

    def __init__(self, prefix: str | None, sufix: str | None, separator="_"):
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
                self.config.separator,
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
        SEPARATOR = "_"

    class FIELDS(CommonDriverMapper.Fields):
        __slots__ = ()
        PREFIX = "prefix"
        SUFIX = "sufix"
        SEPARATOR = "separator"

    @classmethod
    def from_context(
        cls, name: str, context: ObjectContext
    ) -> IDriverConfig | None:
        _ = cls.FIELDS

        resolver = context.find_string(_.RESOLVER).or_none()
        properties = context.find_string_map(_.PROPERTIES).or_else({})

        def read_config(config: ObjectContext) -> EnvironmentConfigDriver | None:
            prefix = config.find_string(_.PREFIX).or_else(cls.DEFAULT.PREFIX)
            sufix = config.find_string(_.SUFIX).or_else(cls.DEFAULT.SUFIX)
            separator = config.find_string(_.SEPARATOR).or_else(
                cls.DEFAULT.SEPARATOR
            )

            return config.construct(
                lambda: EnvironmentConfigDriver(prefix, sufix, separator)
            )

        env_config = context.find_object(_.CONFIG, read_config).or_else(
            EnvironmentConfigDriver(
                cls.DEFAULT.PREFIX, cls.DEFAULT.SUFIX, cls.DEFAULT.SEPARATOR
            )
        )

        if resolver:
            return EnvironmentUnresolvedConfigDriver(
                name, resolver, env_config, properties
            )

        return EnvironmentResolvedConfigDriver(name, env_config)
