from datetime import datetime
from uuid import UUID


class LockFailedException(Exception):
    pass


class Lock:
    __slots__ = ("id", "valid_till", "transaction_id", "holder_id")

    def __init__(
        self, id: UUID, valid_till: datetime, transaction_id: UUID, holder_id: UUID
    ):
        self.id = id
        self.valid_till = valid_till
        self.transaction_id = transaction_id
        self.holder_id = holder_id
