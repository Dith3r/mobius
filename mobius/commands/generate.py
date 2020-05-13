import os
from argparse import Namespace
from datetime import datetime
from pathlib import Path

from mobius.commons.command import (
    Command,
    CommandException,
    Handler,
)


class GenerateHandler(Handler):
    description = "Generate new migration file"

    @classmethod
    def params_add(cls, parser):
        parser.add_argument('-d', '--directory', default='.', help="directory with migration files", required=True)

    @classmethod
    def params_extract(cls, parameters: Namespace) -> str:
        return parameters.directory

    def execute(self, parameters: Namespace):
        generate_command = self.container.commands.generate
        directory = self.params_extract(parameters)
        generate_command.execute(directory)


class GenerateCommandException(CommandException):
    __slots__ = ()

    def __init__(self, code: str):
        super().__init__(f"MIGRATION.GENERATE.{code}")


class DestinationNotDirectoryException(GenerateCommandException):
    __slots__ = ('directory',)

    def __init__(self, directory: str):
        super().__init__("IS_NOT_DIRECTORY")
        self.directory = directory


class DestinationNotWritableDirectoryException(GenerateCommandException):
    __slots__ = ('directory',)

    def __init__(self, directory: str):
        super().__init__("IS_NOT_WRITABLE_DIRECTORY")
        self.directory = directory


class MigrationTemplate:
    __slots__ = ('migration_id',)

    def __init__(self, migration_id: int):
        self.migration_id = migration_id

    def to_str(self) -> str:
        return f"""from mobius import Migration


class Migration{self.migration_id}(Migration):
    def get_id(self) -> int:
        return {self.migration_id}

    def execute(self):
        pass

    def description(self) -> str:
        return ""
"""


class TimestampGenerator:
    __slots__ = ()

    @classmethod
    def unow(cls) -> int:
        pk = int(datetime.utcnow().timestamp() * 100)

        return pk


class GenerateCommand(Command):
    __slots__ = ()

    def execute(self, directory: str):
        migrations_directory = Path(directory)

        if not migrations_directory.is_dir():
            raise DestinationNotDirectoryException(migrations_directory.absolute())

        if not os.access(migrations_directory, os.W_OK):
            raise DestinationNotWritableDirectoryException(migrations_directory.absolute())

        migration_id = TimestampGenerator.unow()

        template = MigrationTemplate(migration_id)

        with migrations_directory / f"{migration_id}.py" as file:
            file.write_text(template.to_str())
