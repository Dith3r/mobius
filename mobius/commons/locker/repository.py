from datetime import datetime
from typing import List
from uuid import UUID

from mobius.commons.locker.model import Lock


class LocksRepository:
    def insert(self, lock: Lock):
        raise NotImplementedError

    def insert_many(self, locks: List[Lock]):
        raise NotImplementedError

    def delete_by_transaction_id(self, transaction_id: UUID):
        raise NotImplementedError

    def delete_by_holder_id(self, holder_id: UUID):
        raise NotImplementedError

    def ensure_indexes(self):
        raise NotImplementedError

    def update_by_transaction_id(
        self, transaction_id: UUID, valid_till: datetime
    ) -> bool:
        raise NotImplementedError
