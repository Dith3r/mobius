from __future__ import annotations

from typing import Any

from mobius.commons.mapping import ObjectContext
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

    def get(self, key: str) -> Any | None:
        return self.data.get(key)

    def __str__(self):
        return str(self.data)


class PlainResolvedConfigDriver(DriverResolvedConfig):
    __slots__ = ()
    config: PlainConfig

    def initialize(self):
        return PlainDriver(self)

    def get(self, key: str) -> Any | None:
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
    def from_context(
        cls, name: str, context: ObjectContext
    ) -> PlainResolvedConfigDriver | None:
        _ = cls.FIELDS

        config = context.find_raw_object(_.CONFIG).or_else({})

        return context.construct(
            lambda: PlainResolvedConfigDriver(name, PlainConfig(config))
        )
