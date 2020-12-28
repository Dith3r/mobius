from io import TextIOWrapper

from mobius.commons.container import cached_property
from mobius.config import (
    MobiusConfig,
    MobiusFileMapper,
)
from mobius.drivers.environment.config import EnvironmentConfigDriverMapper
from mobius.drivers.manager import (
    DriverJsonMapper,
    DriverManager,
)
from mobius.drivers.mongo.config import MongoConfigDriverMapper
from mobius.drivers.mysql.config import MySqlConfigDriverMapper
from mobius.drivers.plain.config import PlainConfigDriverMapper


class Container:
    config: MobiusConfig

    def configure(self, configuration: TextIOWrapper):
        self.config = self.mobius_file_mapper.from_file(configuration)

        return self.config

    @cached_property
    def mobius_file_mapper(self) -> MobiusFileMapper:
        return MobiusFileMapper(self.driver_json_mapper)

    @cached_property
    def driver_json_mapper(self) -> DriverJsonMapper:
        driver_mapper = DriverJsonMapper()

        driver_mapper.register(PlainConfigDriverMapper)
        driver_mapper.register(EnvironmentConfigDriverMapper)
        driver_mapper.register(MongoConfigDriverMapper)
        driver_mapper.register(MySqlConfigDriverMapper)

        return driver_mapper

    @cached_property
    def driver_manager(self) -> DriverManager:
        return DriverManager(self.config.state, self.config.sources.values())
