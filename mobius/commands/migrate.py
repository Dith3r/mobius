import logging
import multiprocessing
from argparse import Namespace
from multiprocessing import Process
from os import scandir
from time import sleep
from typing import Dict
from uuid import UUID, uuid4

from mobius.commons.command import Command, Handler
from mobius.commons.data import chunk, file_md5
from mobius.commons.locker.model import LockFailedException
from mobius.commons.locker.service import Locker
from mobius.commons.logger.model import (
    Failed,
    InProgress,
    Log,
    Skipped,
    Succeed,
    filename_to_id,
)
from mobius.commons.logger.service import Logger
from mobius.drivers.manager import DriverManager
from mobius.migration.runner import (
    FailedResult,
    SkippedResult,
    SuccessResult,
    migration_handler,
)


logger = logging.getLogger("migration")


class MigrateHandler(Handler):
    description = "Run new migrations"

    def execute(self, parameters: Namespace):
        migrate_command = self.container.commands.migrate

        migrate_command.execute(
            parameters.directory, parameters.no_hash, parameters.no_wait
        )

    @classmethod
    def params_add(cls, parser):
        parser.add_argument(
            "-d",
            "--directory",
            default=".",
            help="directory with migration files",
            required=True,
        )
        parser.add_argument(
            "-i",
            "--ignore-hash",
            default=False,
            help="Ignore migration files hashes",
            action="store_true",
            dest="no_hash",
        )
        parser.add_argument(
            "-n",
            "--no-wait",
            default=False,
            help="Don't wait for lock",
            action="store_true",
            dest="no_wait",
        )

    @classmethod
    def params_extract(cls, parameters: Namespace) -> str:
        return parameters.directory


class MigrateCommand(Command):
    GLOBAL_LOCK = UUID(int=0)

    def __init__(self, driver_manager: DriverManager, logger: Logger, locker: Locker):
        self.driver_manager = driver_manager
        self.logger = logger
        self.locker = locker
        self.runtime_id = uuid4()

    def execute(self, directory: str, ignore_hash: bool, no_wait: bool):
        self.driver_manager.resolve_all()
        self.locker.ensure_index()
        retries = True

        while retries:
            try:
                with self.locker.lock(self.GLOBAL_LOCK, self.runtime_id, ttl=90):
                    retries = False
                    self.logger.ensure_index()
                    self.logger.ensure_all_completed()

                    queue = multiprocessing.Queue()

                    migration_files = [
                        dir_entry
                        for dir_entry in scandir(directory)
                        if dir_entry.is_file() and dir_entry.name.endswith(".py")
                    ]

                    migration_files = sorted(
                        migration_files, key=lambda entry: entry.name
                    )

                    for migration_chunk in chunk(migration_files, 100):
                        migration_ids = [
                            filename_to_id(dir_entry.name)
                            for dir_entry in migration_chunk
                        ]

                        logs = self.logger.fetch_by_id(migration_ids)
                        id_logs: Dict[int, Log] = {log.id: log for log in logs}

                        for migration in migration_chunk:
                            migration_hash = file_md5(migration)

                            migration_id = filename_to_id(migration.name)
                            migration_log = id_logs.get(migration_id)

                            logger.info(
                                f"Migration[{migration_id}] starting",
                                extra={"details": {"migrationId": migration_id}},
                            )

                            if migration_log:
                                if migration_log.hash != migration_hash:
                                    message = f"Migration[{migration_id}] changed! Hash: {migration_log.hash} != {migration_hash}"
                                    if not ignore_hash:
                                        raise ValueError(message)
                                    else:
                                        logger.warning(
                                            message,
                                            extra={
                                                "details": {"migrationId": migration_id}
                                            },
                                        )

                                if migration_log.state in (Skipped, Succeed):
                                    logger.info(
                                        f"Migration[{migration_id}]: `{migration_log.msg}` already {migration_log.state}",
                                        extra={
                                            "details": {"migrationId": migration_id}
                                        },
                                    )
                                    continue
                            else:
                                migration_log = Log.new(migration_id, migration_hash)
                                self.logger.insert(migration_log)

                            migration_log.state = InProgress
                            migration_log.msg = None
                            self.logger.update(migration_log)

                            migration_process = Process(
                                target=migration_handler,
                                args=(
                                    self.driver_manager.configs,
                                    migration_id,
                                    migration,
                                    queue,
                                    logger.getEffectiveLevel(),
                                ),
                            )
                            migration_process.start()

                            while migration_process.is_alive():
                                migration_process.join(0.5)
                                logger.debug(
                                    f"Migration[{migration_id}] await",
                                    extra={"details": {"migrationId": migration_id}},
                                )

                            result = queue.get(block=False)

                            if result:
                                if isinstance(result, SuccessResult):
                                    migration_log.state = Succeed
                                elif isinstance(result, SkippedResult):
                                    migration_log.state = Skipped
                                elif isinstance(result, FailedResult):
                                    migration_log.state = Failed

                                migration_log.msg = result.msg
                            else:
                                migration_log.state = Failed
                                migration_log.msg = (
                                    "Process ended with without response on queue"
                                )

                            self.logger.update(migration_log)

                            if migration_log.state == Failed:
                                raise ValueError("Cannot continue")

            except LockFailedException:
                logger.info("Acquiring lock failed")

                if no_wait:
                    retries = False
                else:
                    sleep(1)
