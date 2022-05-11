from argparse import Namespace
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from mobius.container import Container


class Handler:
    description: str

    def __init__(self, container: "Container"):
        self.container = container

    def execute(self, parameters: Namespace):
        raise NotImplementedError

    @classmethod
    def params_add(cls, parser):
        raise NotImplementedError


class Command:
    __slots__ = ()


class CommandException(Exception):
    __slots__ = ("code",)

    def __init__(self, code: str):
        self.code = code

    def __str__(self):
        return f"{self.__class__.__name__}[code={self.code}]"
