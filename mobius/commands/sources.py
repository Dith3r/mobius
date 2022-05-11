from argparse import Namespace

from mobius.commons.command import Handler


class SourcesHandler(Handler):
    description = "Print data sources"

    def execute(self, parameters: Namespace):
        driver_manager = self.container.driver_manager

        driver_manager.resolve_all()
        for config in driver_manager.configs.values():
            print(config)

    @classmethod
    def params_add(cls, parser):
        pass
