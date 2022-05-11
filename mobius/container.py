from io import TextIOWrapper

from mobius.commands.generate import GenerateCommand
from mobius.commands.migrate import MigrateCommand
from mobius.commons.container import cached_property
from mobius.commons.locker.repository import LocksRepository
from mobius.commons.locker.service import Locker
from mobius.commons.logger.repository import LogsRepository
from mobius.commons.logger.service import Logger
from mobius.config import MobiusConfig, MobiusFileMapper
from mobius.drivers.environment.config import EnvironmentConfigDriverMapper
from mobius.drivers.kafka.config import KafkaConfigDriverMapper
from mobius.drivers.manager import DriverJsonMapper, DriverManager
from mobius.drivers.mongo.config import MongoConfigDriverMapper
from mobius.drivers.mysql.config import MySqlConfigDriverMapper
from mobius.drivers.plain.config import PlainConfigDriverMapper


class CommandsContainer:
    def __init__(self, container: "Container"):
        self.container = container

    @cached_property
    def generate(self) -> GenerateCommand:
        return GenerateCommand()

    @cached_property
    def migrate(self) -> MigrateCommand:
        return MigrateCommand(
            self.container.driver_manager, self.container.logger, self.container.locker
        )


class Container:
    config: MobiusConfig
    commands: CommandsContainer

    def configure(self, configuration: TextIOWrapper):
        self.config = self.mobius_file_mapper.from_file(configuration)
        self.commands = CommandsContainer(self)

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
        driver_mapper.register(KafkaConfigDriverMapper)

        return driver_mapper

    @cached_property
    def driver_manager(self) -> DriverManager:
        return DriverManager(
            self.config.state, self.config.locker, self.config.sources.values()
        )

    @cached_property
    def logger(self) -> Logger:
        return Logger(self.logs_repository)

    @cached_property
    def locker(self) -> Locker:
        return Locker(self.locks_repository)

    @cached_property
    def logs_repository(self) -> LogsRepository:
        return self.driver_manager.get_state_driver().get_logs_repository()

    @cached_property
    def locks_repository(self) -> LocksRepository:
        return self.driver_manager.get_locker_driver().get_locks_repository()
