from mobius.drivers.manager import (
    DriverResolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)
from mobius.drivers.plain.driver import PlainDriver


class PlainConfig(IDriverConfig):
    pass


class PlainResolvedConfigDriver(DriverResolvedConfig):
    __slots__ = ()

    def initialize(self):
        return PlainDriver()

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return self.__str__()


class PlainConfigDriverMapper(IConfigDriverMapper):
    JSON_KIND = "PLAIN"
    KIND = PlainResolvedConfigDriver

    class DEFAULT:
        __slots__ = ()

    @classmethod
    def from_json(cls, name: str, data: dict) -> PlainResolvedConfigDriver:
        return PlainResolvedConfigDriver(name, PlainConfig())
