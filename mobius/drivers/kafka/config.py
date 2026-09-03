from __future__ import annotations

from typing import Any, Dict

from mobius.commons.mapping import ObjectContext
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
    def from_context(
        cls, name: str, context: ObjectContext
    ) -> IDriverConfig | None:
        _ = cls.FIELDS

        resolver = context.find_string(_.RESOLVER).or_none()
        properties = context.find_string_map(_.PROPERTIES).or_else({})

        def read_config(config: ObjectContext) -> KafkaConfigDriver | None:
            bootstrap_servers = config.get_string(_.BOOTSTRAP_SERVERS)

            return config.construct(
                lambda: KafkaConfigDriver(bootstrap_servers.require())
            )

        kafka_config = context.get_object(_.CONFIG, read_config).or_none()
        if kafka_config is None:
            return None

        if resolver:
            return KafkaUnresolvedConfigDriver(name, resolver, kafka_config, properties)

        return KafkaResolvedConfigDriver(name, kafka_config)
