from typing import (
    Any,
    Dict,
    Iterable,
    Set,
    Type,
)

from mobius.commons.driver import IDriver


class Source:
    __slots__ = ()


class IDriverConfig:
    pass


class DriverUnresolvedConfig(IDriverConfig):
    name: str
    resolver: str
    properties: Dict[str, str]
    config: Dict[str, Any]

    def __init__(self,
                 name: str,
                 resolver: str,
                 config: Dict[str, Any],
                 properties: Dict[str, str]):
        self.name = name
        self.resolver = resolver
        self.properties = properties
        self.config = config

    def __str__(self):
        return f"{self.__class__.__name__}[name={self.name}, resolver={self.resolver}]"

    def __repr__(self):
        return self.__str__()


class DriverResolvedConfig(IDriverConfig):
    def __init__(self,
                 name: str,
                 config: IDriverConfig):
        self.name = name
        self.config = config

    def initialize(self):
        raise NotImplementedError


class IConfigDriverMapper:
    __slots__ = ()
    KIND: Type[IDriverConfig]
    JSON_KIND: str

    @classmethod
    def from_json(cls, name: str, data: dict) -> IDriverConfig:
        raise NotImplementedError


class CommonDriverMapper:
    __slots__ = ()

    class Fields:
        __slots__ = ()
        KIND = 'kind'
        RESOLVER = 'resolver'
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

    def from_json(self, name: str, data: Any) -> IDriverConfig:
        _ = CommonDriverMapper.Fields

        if not isinstance(data, dict):
            raise RuntimeError("Driver configuration is not a JsonObject")

        kind = data[_.KIND]

        mapper = self._from_json[kind]

        return mapper.from_json(name, data)


class DriverManager:
    __slots__ = ('drivers', 'resolved', 'definitions', 'state_driver')
    drivers: Dict[str, IDriver]
    resolved: Dict[str, DriverResolvedConfig]
    definitions: Dict[str, IDriverConfig]
    source: IDriverConfig

    def __init__(self,
                 state_driver: IDriverConfig,
                 drivers: Iterable[IDriverConfig]):
        self.drivers = {}
        self.resolved = {}
        self.definitions = {}
        self.state_driver = state_driver

        for driver in drivers:
            if isinstance(driver, DriverResolvedConfig):
                self.resolved[driver.name] = driver
                self.drivers[driver.name] = driver.initialize()
            self.definitions[driver.name] = driver

    def get(self, name: str) -> DriverResolvedConfig:
        source = self.resolved.get(name)

        if not source:
            unresolved = self.definitions.get(name)

            if isinstance(unresolved, DriverResolvedConfig):
                raise RuntimeError("Desynchronization")
            else:
                source = self.resolve(unresolved)

        return source

    def resolve(self, unresolved: IDriverConfig) -> DriverResolvedConfig:
        if not isinstance(unresolved, DriverUnresolvedConfig):
            raise ValueError("Cannot resolve resolved config")

        if unresolved.resolver == unresolved.name:
            raise ValueError("Cannot be resolved by itself")

        drivers = set()

        raise NotImplementedError
