from argparse import Namespace

from mobius.commons.container import Container


class Command:
    description: str

    @classmethod
    def parser_fill(cls, parser):
        raise NotImplementedError

    def execute(self, container: Container, parameters: Namespace):
        raise NotImplementedError
