from mobius.commands.generate import GenerateCommand
from mobius.commons.container import cached_property
from mobius.config import MobiusConfig


class CommandsContainer:
    def __init__(self, config: MobiusConfig):
        self.config = config

    @cached_property
    def generate(self) -> GenerateCommand:
        return GenerateCommand()


class Container:
    def __init__(self, config: MobiusConfig):
        self.config = config
        self.commands = CommandsContainer(self.config)
