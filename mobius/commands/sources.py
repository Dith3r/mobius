from argparse import Namespace

from mobius.commons.command import Handler


class SourcesHandler(Handler):
    description = "Print data sources"

    def execute(self, parameters: Namespace):
        driver_manager = self.container.driver_manager
        print(driver_manager.definitions)
        print(driver_manager.resolved)
        print(driver_manager.get("ENV"))

    @classmethod
    def params_add(cls, parser):
        pass

    @classmethod
    def params_extract(cls, parameters: Namespace):
        pass
