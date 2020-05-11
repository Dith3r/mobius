from argparse import (
    ArgumentParser,
    FileType,
)
from typing import Dict

from mobius.commands.dummy import DummyCommand
from mobius.commands.generate import GenerateCommand
from mobius.commons.command import Command
from mobius.config import MobiusConfig

LOG_LEVELS = ["DEBUG", "INFO", "WARN", "ERROR"]


class Container:
    def __init__(self, config: MobiusConfig):
        self.config = config


class Bootstrap:
    parser: ArgumentParser

    commands: Dict[str, Command] = {
        "generate": GenerateCommand,
        "migrate": DummyCommand,
        "difference": DummyCommand
    }

    def __init__(self):
        self.parser = ArgumentParser(prog="mobius")

        self.parser.add_argument('-c', '--config', default="config.json", help="Path to tool configuration", type=FileType('r'), required=True)

        commands = self.parser.add_subparsers(help="command", dest='command', required=True)

        self.parser.add_argument('-l', '--log-level', action='store', choices=LOG_LEVELS, type=str, default="INFO")

        for name, command in self.commands.items():
            if command:
                sub_parser = commands.add_parser(name, help=command.description)
                command.parser_fill(sub_parser)

    def run(self):
        arguments = self.parser.parse_args()
        config_file = MobiusConfig.from_file(arguments.config)
        command = self.commands.get(arguments.command)


def main():
    bootstrap = Bootstrap()
    bootstrap.run()


if __name__ == '__main__':
    main()
