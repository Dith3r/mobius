from abc import ABC
from argparse import Namespace


class Executable(ABC):
    def execute(self, parameters: Namespace):
        raise NotImplementedError


class Command(Executable, ABC):
    description: str

    @classmethod
    def parser_fill(cls, parser):
        raise NotImplementedError
