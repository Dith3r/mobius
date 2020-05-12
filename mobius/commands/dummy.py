from argparse import Namespace

from mobius.commons.command import Command


class DummyCommand(Command):
    description = "dummy command"

    @classmethod
    def parser_fill(cls, parser):
        # this is a placeholder
        pass

    def execute(self, parameters: Namespace):
        # This is a placeholder
        pass
