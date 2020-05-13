from argparse import (
    ArgumentParser,
    FileType,
)
from typing import (
    Dict,
    Type,
)

from mobius.commands.dummy import DummyHandler
from mobius.commands.generate import (
    GenerateHandler,
)
from mobius.commons.command import (
    Handler,
)
from mobius.config import MobiusConfig
from mobius.container import Container

LOG_LEVELS = ["DEBUG", "INFO", "WARN", "ERROR"]


class Bootstrap:
    parser: ArgumentParser

    commands: Dict[str, Type[Handler]] = {
        "generate": GenerateHandler,
        "migrate": DummyHandler,
        "difference": DummyHandler,
        "sources": DummyHandler,
    }

    def __init__(self):
        self.parser = ArgumentParser(prog="mobius")

        self.parser.add_argument('-c', '--config', default="config.json", help="Path to tool configuration", type=FileType('r'), required=True)

        commands = self.parser.add_subparsers(help="command", dest='command', required=True)

        self.parser.add_argument('-l', '--log-level', action='store', choices=LOG_LEVELS, type=str, default="INFO")

        for name, command in self.commands.items():
            if command:
                sub_parser = commands.add_parser(name, help=command.description)
                command.params_add(sub_parser)

    def run(self):
        arguments = self.parser.parse_args()
        config_file = MobiusConfig.from_file(arguments.config)

        container = Container(config_file)
        handler = self.commands[arguments.command](container)
        handler.execute(arguments)


def main():
    bootstrap = Bootstrap()
    bootstrap.run()


if __name__ == '__main__':
    main()
