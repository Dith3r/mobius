import contextlib
import logging
import sys
import traceback
from dataclasses import dataclass
from importlib import util
from multiprocessing import Queue
from os import DirEntry
from typing import Any, Dict, List, Optional

from mobius import Migration, MigrationFailedException, MigrationSkippedException
from mobius.commons.driver import IDriver
from mobius.drivers.manager import DriverResolvedConfig


logger = logging.getLogger("runner")


@dataclass
class Result:
    pass


@dataclass
class SuccessResult(Result):
    msg: Optional[str] = None


@dataclass
class SkippedResult(Result):
    msg: Optional[str] = None


@dataclass
class FailedResult(Result):
    trace: List[str]
    msg: Optional[str] = None


class DriverManager:
    def __init__(self, connection_configs: Dict[str, DriverResolvedConfig]):
        self.connection_configs = connection_configs

    @contextlib.contextmanager
    def get(self, connection_name: str) -> Any:
        config = self.connection_configs.get(connection_name)
        if config is None:
            raise ValueError(f"Unknown connection: {connection_name}")

        driver: IDriver = config.initialize()
        connection = None
        try:
            connection = driver.connection()
            yield connection
        finally:
            if connection:
                driver.close(connection)


def close(self):
    pass


def migration_handler(
    connection_configs: Dict[str, DriverResolvedConfig],
    migration_id: str,
    migration_file: DirEntry,
    message: Queue,
):
    try:
        logger.info(f"Migration[{migration_id}]: loading file: {migration_file.path}")
        spec = util.spec_from_file_location(
            migration_file.name, location=migration_file
        )
        migration_module = util.module_from_spec(spec)
        spec.loader.exec_module(migration_module)

        migration_class = migration_module.__dict__[f"Migration{migration_id}"]
        manager = DriverManager(connection_configs)
        migration: Migration = migration_class(manager)

        logger.info(f"Migration[{migration_id}]: `{migration.description()}`")
        logger.info(f"Migration[{migration_id}]: Validate")
        migration.validate()
        logger.info(f"Migration[{migration_id}]: Executing")
        migration.execute()
        logger.info(f"Migration[{migration_id}]: Success")

        message.put(SuccessResult(migration.description()))

    except MigrationSkippedException as exception:
        logger.info(f"Migration[{migration_id}]: Skipped")

        message.put(SkippedResult(msg=exception.msg))

    except MigrationFailedException as exception:
        logger.info(f"Migration[{migration_id}]: Failed", exc_info=True)

        message.put(
            FailedResult(
                trace=list(
                    traceback.TracebackException.from_exception(exception).format()
                ),
                msg=exception.msg,
            )
        )

    except Exception as exception:
        logger.info(f"Migration[{migration_id}]: Unhandled exception", exc_info=True)

        message.put(
            FailedResult(
                trace=list(
                    traceback.TracebackException.from_exception(exception).format()
                ),
                msg=str(exception),
            )
        )
        sys.exit(-1)
