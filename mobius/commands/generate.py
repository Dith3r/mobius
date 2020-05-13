import os
from argparse import Namespace
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


class GenerateCommand(Command):
    def execute(self, directory: str):
        migrations_directory = Path(directory)

        if not migrations_directory.is_dir():
            raise DestinationNotDirectoryException(migrations_directory.absolute())

        if not os.access(migrations_directory, os.W_OK):
            raise DestinationNotWritableDirectoryException(migrations_directory.absolute())
