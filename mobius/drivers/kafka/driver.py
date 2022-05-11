from typing import TYPE_CHECKING, Any

from confluent_kafka.admin import AdminClient


if TYPE_CHECKING:
    from mobius.drivers.kafka.config import KafkaConfigDriver

from mobius.commons.driver import IDriver


class KafkaDriver(IDriver):
    def __init__(self, name: str, config: "KafkaConfigDriver"):
        self.name = name
        self.config = config

    def connection(self) -> Any:
        return AdminClient({"bootstrap.servers": self.config.bootstrap_servers})

    def close(self, connection: Any):
        pass
