from typing import Any, Optional

from mobius.drivers.manager import (
    CommonDriverMapper,
    DriverResolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)
from mobius.drivers.plain.driver import PlainDriver


class PlainConfig(IDriverConfig):
    def __init__(self, data: dict):
        self.data = data

    def get(self, key: str) -> Optional[Any]:
        return self.data.get(key)

    def __str__(self):
        return str(self.data)


class PlainResolvedConfigDriver(DriverResolvedConfig):
    __slots__ = ()
    config: PlainConfig

    def initialize(self):
        return PlainDriver(self)

    def get(self, key: str) -> Optional[Any]:
        return self.config.get(key)

    def __str__(self):
        return f"{self.__class__.__name__}[name={self.name}, config={self.config}]"

    def __repr__(self):
        return self.__str__()


class PlainConfigDriverMapper(IConfigDriverMapper):
    JSON_KIND = "PLAIN"
    KIND = PlainResolvedConfigDriver

    class FIELDS(CommonDriverMapper.Fields):
        __slots__ = ()

    @classmethod
    def from_json(cls, name: str, data: dict) -> PlainResolvedConfigDriver:
        _ = cls.FIELDS

        config = data.get(_.CONFIG, {})

        if not isinstance(config, dict):
            raise RuntimeError("Invalid config for driver %s", name)

        return PlainResolvedConfigDriver(name, PlainConfig(config))
