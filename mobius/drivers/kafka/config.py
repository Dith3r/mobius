from typing import Any, Dict

from mobius.drivers.kafka.driver import KafkaDriver
from mobius.drivers.manager import (
    CommonDriverMapper,
    DriverResolvedConfig,
    DriverUnresolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)


class KafkaConfigDriver(IDriverConfig):
    bootstrap_servers: str

    def __init__(self, boostrap_servers: str):
        self.bootstrap_servers = boostrap_servers


class KafkaResolvedConfigDriver(DriverResolvedConfig):
    config: KafkaConfigDriver

    def __init__(self, name: str, config: KafkaConfigDriver):
        super().__init__(name, config)

    def initialize(self) -> KafkaDriver:
        return KafkaDriver(self.name, self.config)

    def __str__(self):
        return f"{self.__class__.__name__}[name={self.name},config={self.config}]"


class KafkaUnresolvedConfigDriver(DriverUnresolvedConfig):
    config: KafkaConfigDriver

    def __init__(
        self,
        name: str,
        resolver: str,
        config: KafkaConfigDriver,
        properties: Dict[str, str],
    ):
        super().__init__(name, resolver, config, properties)

    def resolve(self, resolved_properties: Dict[str, Any]) -> DriverResolvedConfig:
        mongo_config = KafkaConfigDriver(
            boostrap_servers=self.config.bootstrap_servers % resolved_properties
        )

        return KafkaResolvedConfigDriver(self.name, mongo_config)


class KafkaConfigDriverMapper(IConfigDriverMapper):
    __slots__ = ()
    JSON_KIND = "KAFKA"
    KIND = KafkaConfigDriver

    class FIELDS(CommonDriverMapper.Fields):
        __slots__ = ()
        BOOTSTRAP_SERVERS = "bootstrapServers"

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

        bootstrap_servers = config.get(_.BOOTSTRAP_SERVERS)

        if resolver:
            return KafkaUnresolvedConfigDriver(
                name,
                resolver,
                KafkaConfigDriver(bootstrap_servers),
                properties,
            )
        else:
            return KafkaResolvedConfigDriver(name, KafkaConfigDriver(bootstrap_servers))
