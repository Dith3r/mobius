class MigrationException:
    __slots__ = ()


class MigrationSkippedException(MigrationException):
    __slots__ = ()


class MigrationFailedException(MigrationException):
    __slots__ = ()


class Migration:
    __slots__ = ()

    def __init__(self, manager, logger):
        ...

    def validate(self):
        raise NotImplementedError

    def execute(self):
        raise NotImplementedError

    def description(self):
        raise NotImplementedError
