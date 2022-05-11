from typing import Optional


class MigrationException(Exception):
    __slots__ = ()


class MigrationSkippedException(MigrationException):
    def __init__(self, msg: Optional[str] = None):
        self.msg = msg


class MigrationFailedException(MigrationException):
    def __init__(self, msg: Optional[str] = None):
        self.msg = msg


class Migration:
    def __init__(self, manager):
        self.manager = manager

    def validate(self):
        raise NotImplementedError

    def execute(self):
        raise NotImplementedError

    def description(self):
        raise NotImplementedError
