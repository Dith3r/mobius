import json
from io import TextIOWrapper
from typing import Dict

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
    def from_json(cls, raw_json: dict) -> MobiusSettings:
        _ = cls.Fields

        if not isinstance(raw_json, dict):
            raise RuntimeError("Settings configuration is not a JsonObject")

        defaults = MobiusSettings()

        return MobiusSettings(
            lock_ttl=int(raw_json.get(_.LOCK_TTL, defaults.lock_ttl)),
            lock_retry_interval=float(
                raw_json.get(_.LOCK_RETRY_INTERVAL, defaults.lock_retry_interval)
            ),
        )


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

        state = raw_json[_.STATE]
        locker = raw_json[_.LOCKER]
        sources = raw_json[_.SOURCES]

        locker_config = driver_config_mapper.from_json("locker", locker)

        state_config = driver_config_mapper.from_json("state", state)

        sources = {
            name: driver_config_mapper.from_json(name, driver_config)
            for name, driver_config in sources.items()
        }

        settings = MobiusSettingsJsonMapper.from_json(raw_json.get(_.SETTINGS, {}))

        return MobiusConfig(state_config, locker_config, sources, settings)


class MobiusFileMapper:
    __slots__ = ("driver_mapper",)

    def __init__(self, driver_mapper: DriverJsonMapper):
        self.driver_mapper = driver_mapper

    def from_file(self, file: TextIOWrapper) -> MobiusConfig:
        with file:
            contents = json.load(file)

        return MobiusJsonMapper.from_json(contents, self.driver_mapper)
