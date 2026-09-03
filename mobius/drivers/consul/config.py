from __future__ import annotations

from typing import Any, Dict

from mobius.commons.mapping import ObjectContext
from mobius.drivers.consul.driver import ConsulDriver
from mobius.drivers.manager import (
    CommonDriverMapper,
    DriverResolvedConfig,
    DriverUnresolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)


class ConsulConfigDriver(IDriverConfig):
    address: str
    token: str | None
    prefix: str
    connect_timeout: int

    def __init__(
        self,
        address: str,
        token: str | None,
        prefix: str,
        connect_timeout: int,
    ):
        self.address = address
        self.token = token
        self.prefix = prefix
        self.connect_timeout = connect_timeout

    def __str__(self):
        # token deliberately omitted: it is a credential
        return (
            f"{self.__class__.__name__}[address={self.address}, "
            f"prefix={self.prefix}, connect_timeout={self.connect_timeout}, "
            f"token={'set' if self.token else 'none'}]"
        )


class ConsulResolvedConfigDriver(DriverResolvedConfig):
    config: ConsulConfigDriver

    def __init__(self, name: str, config: ConsulConfigDriver):
        super().__init__(name, config)

    def initialize(self) -> ConsulDriver:
        return ConsulDriver(self.name, self.config)

    def __str__(self):
        return f"{self.__class__.__name__}[name={self.name},config={self.config}]"


class ConsulUnresolvedConfigDriver(DriverUnresolvedConfig):
    config: ConsulConfigDriver

    def __init__(
        self,
        name: str,
        resolver: str,
        config: ConsulConfigDriver,
        properties: Dict[str, str],
    ):
        super().__init__(name, resolver, config, properties)

    def resolve(self, resolved_properties: Dict[str, Any]) -> DriverResolvedConfig:
        def interpolate(value: str | None) -> str | None:
            if value is None:
                return None
            return value % resolved_properties

        consul_config = ConsulConfigDriver(
            address=interpolate(self.config.address),
            token=interpolate(self.config.token),
            prefix=interpolate(self.config.prefix),
            connect_timeout=self.config.connect_timeout,
        )

        return ConsulResolvedConfigDriver(self.name, consul_config)


class ConsulConfigDriverMapper(IConfigDriverMapper):
    __slots__ = ()
    JSON_KIND = "CONSUL"
    KIND = ConsulConfigDriver

    class DEFAULT:
        __slots__ = ()
        PREFIX = ""
        CONNECT_TIMEOUT = 10

    class FIELDS(CommonDriverMapper.Fields):
        __slots__ = ()
        ADDRESS = "address"
        TOKEN = "token"
        PREFIX = "prefix"
        CONNECT_TIMEOUT = "connectTimeout"

    @classmethod
    def from_context(
        cls, name: str, context: ObjectContext
    ) -> IDriverConfig | None:
        _ = cls.FIELDS

        resolver = context.find_string(_.RESOLVER).or_none()
        properties = context.find_string_map(_.PROPERTIES).or_else({})

        def read_config(config: ObjectContext) -> ConsulConfigDriver | None:
            address = config.get_string(_.ADDRESS)
            token = config.find_string(_.TOKEN).or_none()
            prefix = config.find_string(_.PREFIX).or_else(cls.DEFAULT.PREFIX)
            connect_timeout = config.find_int(_.CONNECT_TIMEOUT).or_else(
                cls.DEFAULT.CONNECT_TIMEOUT
            )

            return config.construct(
                lambda: ConsulConfigDriver(
                    address.require(), token, prefix, connect_timeout
                )
            )

        consul_config = context.get_object(_.CONFIG, read_config).or_none()
        if consul_config is None:
            return None

        if resolver:
            return ConsulUnresolvedConfigDriver(
                name, resolver, consul_config, properties
            )

        return ConsulResolvedConfigDriver(name, consul_config)
