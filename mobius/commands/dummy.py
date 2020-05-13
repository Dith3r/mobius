from argparse import Namespace

from mobius.commons.command import (
    Handler,
)


class DummyHandler(Handler):
    description = "dummy command"

    def execute(self, parameters: Namespace):
        # pass through
        pass

    @classmethod
    def params_add(cls, parser):
        # pass through
        pass

    @classmethod
    def params_extract(cls, parameters: Namespace):
        # pass through
        pass
