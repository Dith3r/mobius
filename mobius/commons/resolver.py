from typing import (
    Any,
    Dict,
)


class IResolver:
    __slots__ = ()

    def get(self, name: str) -> str:
        raise NotImplementedError

    def resolve(self, properties: Dict[str, str]) -> Dict[str, Any]:
        raise NotImplementedError
