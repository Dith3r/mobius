from __future__ import annotations

import json
from io import TextIOWrapper
from typing import Dict

from mobius.commons.mapping import (
    InvalidValueError,
    ObjectContext,
    map_object,
)
from mobius.drivers.manager import DriverJsonMapper, IDriverConfig


class MobiusSettings:
    __slots__ = ("lock_ttl", "lock_retry_interval")
    lock_ttl: int
    lock_retry_interval: float

    def __init__(self, lock_ttl: int = 90, lock_retry_interval: float = 1.0):
        if lock_ttl <= 0:
            raise ValueError(f"lockTtl must be positive, got: {lock_ttl}")

        if lock_retry_interval <= 0:
            raise ValueError(
                f"lockRetryInterval must be positive, got: {lock_retry_interval}"
            )

        self.lock_ttl = lock_ttl
        self.lock_retry_interval = lock_retry_interval

    def __str__(self):
        return (
            f"{self.__class__.__name__}[lock_ttl={self.lock_ttl}, "
            f"lock_retry_interval={self.lock_retry_interval}]"
        )


class MobiusConfig:
    __slots__ = ("state", "locker", "sources", "settings")
    state: IDriverConfig
    locker: IDriverConfig
    sources: Dict[str, IDriverConfig]
    settings: MobiusSettings

    def __init__(
        self,
        state: IDriverConfig,
        locker: IDriverConfig,
        sources: Dict[str, IDriverConfig],
        settings: MobiusSettings,
    ):
        self.state = state
        self.locker = locker
        self.sources = sources
        self.settings = settings


class MobiusSettingsJsonMapper:
    __slots__ = ()

    class Fields:
        __slots__ = ()
        LOCK_TTL = "lockTtl"
        LOCK_RETRY_INTERVAL = "lockRetryInterval"

    @classmethod
    def from_context(cls, context: ObjectContext) -> MobiusSettings | None:
        _ = cls.Fields
        defaults = MobiusSettings()

        positive = InvalidValueError(reason="must be positive")

        lock_ttl = (
            context.find_int(_.LOCK_TTL)
            .must(positive, lambda value: value > 0)
            .or_else(defaults.lock_ttl)
        )

        lock_retry_interval = (
            context.find_float(_.LOCK_RETRY_INTERVAL)
            .must(positive, lambda value: value > 0)
            .or_else(defaults.lock_retry_interval)
        )

        return context.construct(
            lambda: MobiusSettings(lock_ttl, lock_retry_interval)
        )

    @classmethod
    def from_json(cls, raw_json) -> MobiusSettings:
        return map_object(raw_json, cls.from_context)


class MobiusJsonMapper:
    __slots__ = ()

    class Fields:
        __slots__ = ()
        STATE = "state"
        LOCKER = "locker"
        SOURCES = "sources"
        SETTINGS = "settings"

    @classmethod
    def from_json(
        cls, raw_json: dict, driver_config_mapper: DriverJsonMapper
    ) -> MobiusConfig:
        _ = cls.Fields

        def read(context: ObjectContext) -> MobiusConfig | None:
            state = context.get_object(
                _.STATE, lambda c: driver_config_mapper.from_context("state", c)
            )
            locker = context.get_object(
                _.LOCKER, lambda c: driver_config_mapper.from_context("locker", c)
            )

            def read_sources(
                sources: ObjectContext,
            ) -> Dict[str, IDriverConfig | None]:
                return {
                    name: sources.get_object(
                        name, lambda c: driver_config_mapper.from_context(name, c)
                    ).or_none()
                    for name in sources.node
                }

            sources = context.get_object(_.SOURCES, read_sources)

            settings = context.find_object(
                _.SETTINGS, MobiusSettingsJsonMapper.from_context
            ).or_else(MobiusSettings())

            return context.construct(
                lambda: MobiusConfig(
                    state.require(), locker.require(), sources.require(), settings
                )
            )

        return map_object(raw_json, read)


class MobiusFileMapper:
    __slots__ = ("driver_mapper",)

    def __init__(self, driver_mapper: DriverJsonMapper):
        self.driver_mapper = driver_mapper

    def from_file(self, file: TextIOWrapper) -> MobiusConfig:
        with file:
            contents = json.load(file)

        return MobiusJsonMapper.from_json(contents, self.driver_mapper)
