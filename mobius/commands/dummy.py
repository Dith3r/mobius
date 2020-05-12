from argparse import Namespace

from mobius.commons.command import Command
from mobius.commons.container import Container


class DummyCommand(Command):
    description = "dummy command"

    @classmethod
    def parser_fill(cls, parser):
        # this is a placeholder
        pass

    def execute(self, container: Container, parameters: Namespace):
        # This is a placeholder
        pass
