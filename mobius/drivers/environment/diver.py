import os
from typing import TYPE_CHECKING, Any, Dict

from mobius.commons.driver import IDriver
from mobius.commons.resolver import IResolver


if TYPE_CHECKING:
    from mobius.drivers.environment.config import EnvironmentResolvedConfigDriver


class EnvironmentDriver(IDriver, IResolver):
    def connection(self) -> Any:
        return self.data

    def close(self, connection: Any):
        pass

    resolved: "EnvironmentResolvedConfigDriver"

    def __init__(self, config: "EnvironmentResolvedConfigDriver"):
        self.data = os.environ.copy()
        self.resolved = config

        self.pattern = self.resolved.config.separator.join(
            filter(
                lambda s: s,
                [self.resolved.config.prefix, "%s", self.resolved.config.sufix],
            )
        )

    def get(self, name: str) -> str:
        key = self.pattern % name

        return self.data.get(key)

    def resolve(self, properties: Dict[str, str]) -> Dict[str, Any]:
        resolved = {key: self.get(value) for key, value in properties.items()}

        return resolved
