from typing import (
    Any,
    Dict,
)

from mobius.commons.driver import IDriver
from mobius.commons.resolver import IResolver


class PlainDriver(IDriver, IResolver):
    __slots__ = ()

    def get(self, name: str) -> str:
        return name

    def resolve(self, properties: Dict[str, str]) -> Dict[str, Any]:
        resolved = {k: v for k, v in properties.items()}

        return resolved
