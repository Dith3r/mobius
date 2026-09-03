from __future__ import annotations

import logging
from argparse import Namespace
from os import scandir
from typing import Dict, List

from mobius.commons.command import Command, Handler
from mobius.commons.data import chunk, file_md5
from mobius.commons.logger.model import (
    Log,
    Skipped,
    Succeed,
    filename_to_id,
    is_migration_filename,
)
from mobius.commons.logger.service import Logger


logger = logging.getLogger("difference")


class MigrationDifference:
    __slots__ = ("name", "id", "reason")

    def __init__(self, name: str, id: int, reason: str):
        self.name = name
        self.id = id
        self.reason = reason

    def __str__(self):
        return f"{self.name} ({self.reason})"

    def __repr__(self):
        return self.__str__()


class DifferenceHandler(Handler):
    description = "Show migrations not yet applied to the state store"

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

    def execute(self, parameters: Namespace):
        difference_command = self.container.commands.difference

        differences = difference_command.execute(
            parameters.directory, parameters.no_hash
        )

        if not differences:
            print("All migrations applied.")
            return

        print(f"{len(differences)} migration(s) not applied:")
        for difference in differences:
            print(f"  {difference}")


class DifferenceCommand(Command):
    COMPLETED = (Skipped, Succeed)

    def __init__(self, logger: Logger):
        self.logger = logger

    def execute(
        self, directory: str, ignore_hash: bool = False
    ) -> List[MigrationDifference]:
        self.logger.ensure_index()

        files = [
            dir_entry for dir_entry in scandir(directory) if dir_entry.is_file()
        ]

        ignored = sorted(
            dir_entry.name
            for dir_entry in files
            if dir_entry.name.endswith(".py")
            and not is_migration_filename(dir_entry.name)
        )
        if ignored:
            logger.warning(
                f"Ignoring python files that are not migrations "
                f"(name must be <numeric id>.py): {ignored}"
            )

        migration_files = sorted(
            (
                dir_entry
                for dir_entry in files
                if is_migration_filename(dir_entry.name)
            ),
            key=lambda dir_entry: dir_entry.name,
        )

        differences: List[MigrationDifference] = []

        for files_chunk in chunk(migration_files, 100):
            migration_ids = [
                filename_to_id(dir_entry.name) for dir_entry in files_chunk
            ]

            logs = self.logger.fetch_by_id(migration_ids)
            id_logs: Dict[int, Log] = {log.id: log for log in logs}

            for dir_entry in files_chunk:
                migration_id = filename_to_id(dir_entry.name)
                log = id_logs.get(migration_id)

                if log is None:
                    differences.append(
                        MigrationDifference(dir_entry.name, migration_id, "never run")
                    )
                elif log.state not in self.COMPLETED:
                    differences.append(
                        MigrationDifference(
                            dir_entry.name, migration_id, f"state: {log.state}"
                        )
                    )
                elif not ignore_hash and log.hash != file_md5(dir_entry):
                    differences.append(
                        MigrationDifference(
                            dir_entry.name, migration_id, "applied but file changed"
                        )
                    )

        return differences
