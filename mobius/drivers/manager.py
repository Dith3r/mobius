from typing import (
    Any,
    Dict,
    Set,
    Type,
)


class DriverConfig:
    __slots__ = ()


class IConfigDriverMapper:
    __slots__ = ()
    KIND: Type
    JSON_KIND: str

    @classmethod
    def from_json(cls, data: dict) -> DriverConfig:
        raise NotImplementedError


class CommonDriverMapper:
    __slots__ = ()

    class Fields:
        __slots__ = ()
        KIND = 'kind'
        RESOLVE = 'resolve'
        PROPERTIES = 'properties'
        CONFIG = 'config'


class DriverJsonMapper:
    __slots__ = ('all', '_from_json')
    all: Set[Type[IConfigDriverMapper]]
    _from_json: Dict[str, Type[IConfigDriverMapper]]

    def __init__(self):
        self.all = set()
        self._from_json = {}

    def register(self, mapper: Type[IConfigDriverMapper]):
        if mapper.JSON_KIND in self._from_json:
            raise ValueError(f"Conflicting type [{mapper.JSON_KIND}]")

        self.all.add(mapper)
        self._from_json[mapper.JSON_KIND] = mapper

    def from_json(self, data: Any) -> DriverConfig:
        ...
