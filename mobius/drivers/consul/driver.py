from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

import httpx

from mobius.commons.driver import IDriver
from mobius.commons.resolver import IResolver


if TYPE_CHECKING:
    from mobius.drivers.consul.config import ConsulConfigDriver


class ConsulDriver(IDriver, IResolver):
    def __init__(
        self,
        name: str,
        config: "ConsulConfigDriver",
        transport: httpx.BaseTransport | None = None,
    ):
        self.name = name
        self.config = config
        self._transport = transport
        self._client: httpx.Client | None = None

    def connection(self) -> Any:
        return self._get_client()

    def close(self, connection: Any):
        connection.close()
        self._client = None

    def get(self, name: str) -> str | None:
        key = self._key(name)

        response = self._get_client().get(f"/v1/kv/{key}", params={"raw": "true"})

        if response.status_code == 404:
            return None

        response.raise_for_status()

        return response.text

    def resolve(self, properties: Dict[str, str]) -> Dict[str, Any]:
        return {key: self.get(value) for key, value in properties.items()}

    def _key(self, name: str) -> str:
        prefix = self.config.prefix
        if not prefix:
            return name

        return f"{prefix.rstrip('/')}/{name}"

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            headers = {}
            if self.config.token:
                headers["X-Consul-Token"] = self.config.token

            self._client = httpx.Client(
                base_url=self.config.address,
                headers=headers,
                timeout=self.config.connect_timeout,
                transport=self._transport,
            )

        return self._client

    def __str__(self):
        return f"{self.__class__.__name__}[name=`{self.name}`]"
