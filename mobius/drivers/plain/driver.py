from typing import TYPE_CHECKING, Any, Dict, Optional


if TYPE_CHECKING:
    from mobius.drivers.plain.config import PlainResolvedConfigDriver

from mobius.commons.driver import IDriver
from mobius.commons.resolver import IResolver


class PlainDriver(IDriver, IResolver):
    __slots__ = ("config",)

    def __init__(self, config: "PlainResolvedConfigDriver"):
        self.config = config

    def get(self, name: str, required: bool = False) -> Optional[str]:
        result = self.config

        if result is None:
            raise ValueError(f"Value {name} is not defined in {self.config.name}")

        return name

    def resolve(self, properties: Dict[str, str]) -> Dict[str, Any]:
        resolved = {k: v for k, v in properties.items()}

        return resolved
