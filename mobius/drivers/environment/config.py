from typing import (
    Optional,
)

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
    name: Optional[str]

    def __init__(self,
                 prefix: Optional[str],
                 sufix: Optional[str]):
        self.prefix = prefix
        self.sufix = sufix

    def __str__(self):
        return f"{self.__class__.__name__}[name={self.name}, prefix={self.prefix}, sufix={self.sufix}]"

    def __repr__(self):
        return self.__str__()


class EnvironmentResolvedConfigDriver(DriverResolvedConfig):
    def __init__(self,
                 name: str,
                 config: EnvironmentConfigDriver):
        super().__init__(name, config)

    def initialize(self):
        pass


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

        prefix = config.get(_.PREFIX) or cls.DEFAULT.PREFIX
        sufix = config.get(_.SUFIX) or cls.DEFAULT.SUFIX

        if resolver:
            return DriverUnresolvedConfig(name,
                                          resolver,
                                          config,
                                          properties)
        else:
            return EnvironmentResolvedConfigDriver(name,
                                                   EnvironmentConfigDriver(prefix, sufix))
