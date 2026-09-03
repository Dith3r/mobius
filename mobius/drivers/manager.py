from __future__ import annotations

from typing import Any, Dict, Iterable, Set, Type

from mobius.commons.driver import IDriver
from mobius.commons.locker.service import ILockerDriver
from mobius.commons.logger.service import IStateDriver
from mobius.commons.mapping import InvalidValueError, ObjectContext, map_object
from mobius.commons.resolver import IResolver


class Source:
    __slots__ = ()


class IDriverConfig:
    pass


class DriverResolvedConfig(IDriverConfig):
    def __init__(self, name: str, config: IDriverConfig):
        self.name = name
        self.config = config

    def initialize(self):
        raise NotImplementedError


class DriverUnresolvedConfig(IDriverConfig):
    name: str
    resolver: str
    properties: Dict[str, str]
    config: IDriverConfig

    def __init__(
        self,
        name: str,
        resolver: str,
        config: IDriverConfig,
        properties: Dict[str, str],
    ):
        self.name = name
        self.resolver = resolver
        self.properties = properties
        self.config = config

    def __str__(self):
        return f"{self.__class__.__name__}[name={self.name}, resolver={self.resolver}]"

    def __repr__(self):
        return self.__str__()

    def resolve(self, config: Dict[str, Any]) -> DriverResolvedConfig:
        raise NotImplementedError


class IConfigDriverMapper:
    __slots__ = ()
    KIND: Type[IDriverConfig]
    JSON_KIND: str

    @classmethod
    def from_context(cls, name: str, context: ObjectContext) -> IDriverConfig | None:
        raise NotImplementedError

    @classmethod
    def from_json(cls, name: str, data: Any) -> IDriverConfig:
        return map_object(data, lambda context: cls.from_context(name, context))


class CommonDriverMapper:
    __slots__ = ()

    class Fields:
        __slots__ = ()
        KIND = "kind"
        RESOLVER = "resolver"
        PROPERTIES = "properties"
        CONFIG = "config"


class DriverJsonMapper:
    __slots__ = ("all", "_from_json")
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

    def from_context(
        self, name: str, context: ObjectContext
    ) -> IDriverConfig | None:
        _ = CommonDriverMapper.Fields

        kind = context.get_string(_.KIND).or_none()
        if kind is None:
            return None

        mapper = self._from_json.get(kind)
        if mapper is None:
            context.report(
                InvalidValueError(kind=kind, known=sorted(self._from_json)),
                field=_.KIND,
            )
            return None

        return mapper.from_context(name, context)

    def from_json(self, name: str, data: Any) -> IDriverConfig:
        return map_object(data, lambda context: self.from_context(name, context))


class DriverManager:
    drivers: Dict[str, IDriver]
    configs: Dict[str, IDriverConfig]

    locker_config: IDriverConfig
    locker_driver: ILockerDriver | None

    state_config: IDriverConfig
    state_driver: IStateDriver | None

    def __init__(
        self,
        state_driver_config: IDriverConfig,
        locker_driver_config: IDriverConfig,
        driver_configs: Iterable[IDriverConfig],
    ):
        self.drivers = {}
        self.configs = {}

        self.state_config = state_driver_config
        self.state_driver = None

        self.locker_config = locker_driver_config
        self.locker_driver = None

        for config in driver_configs:
            if isinstance(config, DriverResolvedConfig):
                self.drivers[config.name] = config.initialize()
            self.configs[config.name] = config

    def get(self, name: str) -> IDriver:
        driver = self.drivers.get(name)

        if not driver:
            driver_config = self.get_config(name)
            self.drivers[name] = driver_config.initialize()

        return self.drivers[name]

    def get_config(self, name: str) -> DriverResolvedConfig:
        driver_config = self.configs.get(name)

        if not driver_config:
            raise RuntimeError("not found")

        if isinstance(driver_config, DriverUnresolvedConfig):
            driver_config = self.resolve(driver_config)
            self.configs[driver_config.name] = driver_config

        return driver_config

    def resolve(self, unresolved: IDriverConfig) -> DriverResolvedConfig:
        if not isinstance(unresolved, DriverUnresolvedConfig):
            raise ValueError("Cannot resolve resolved config")

        if unresolved.resolver == unresolved.name:
            raise ValueError("Cannot be resolved by itself")

        resolver = self.get(unresolved.resolver)
        if not isinstance(resolver, IResolver):
            raise ValueError(f"Driver {unresolved.resolver} is not resolver")
        resolved_properties = resolver.resolve(unresolved.properties)

        # fail closed: a property the resolver could not find must abort the
        # run, never interpolate as the string "None"
        missing = sorted(
            f"{key} ({unresolved.properties[key]})"
            for key, value in resolved_properties.items()
            if value is None
        )
        if missing:
            raise ValueError(
                f"Driver `{unresolved.name}`: resolver `{unresolved.resolver}` "
                f"returned no value for: {', '.join(missing)}"
            )

        config = unresolved.resolve(resolved_properties)

        self.configs[unresolved.name] = config

        return config

    def resolve_all(self):
        for connection_name in self.configs:
            self.get_config(connection_name)

    def get_state_driver(self) -> IStateDriver:
        if isinstance(self.state_config, DriverUnresolvedConfig):
            self.state_config: DriverResolvedConfig = self.resolve(self.state_config)

        if self.state_driver is None:
            state_driver = self.state_config.initialize()
            if not isinstance(state_driver, IStateDriver):
                raise ValueError(
                    f"Driver `{self.state_config.name}` cannot be used as state"
                )

            self.state_driver = state_driver

        return self.state_driver

    def get_locker_driver(self) -> ILockerDriver:
        if isinstance(self.locker_config, DriverUnresolvedConfig):
            self.locker_config: DriverResolvedConfig = self.resolve(self.locker_config)

        if self.locker_driver is None:
            locker_driver = self.locker_config.initialize()
            if not isinstance(locker_driver, ILockerDriver):
                raise ValueError(
                    f"Driver `{self.locker_config.name}` cannot be used as locker"
                )

            self.locker_driver = locker_driver

        return self.locker_driver
