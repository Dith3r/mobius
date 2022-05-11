from typing import Any


class IDriver:
    __slots__ = ()

    def connection(self) -> Any:
        raise NotImplementedError

    def close(self, connection: Any):
        raise NotImplementedError
