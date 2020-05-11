from mobius.commons.command import Command
from mobius.commons.container import Container


class GenerateCommand(Command):
    description = "Generate new migration file"

    @classmethod
    def parser_fill(cls, parser):
        parser.add_argument('-d', '--directory', default='.', help="directory with migration files", required=True)

    def execute(self, container: Container):
        print("puff")
