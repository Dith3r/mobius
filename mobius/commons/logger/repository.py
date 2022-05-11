from typing import List

from mobius.commons.logger.model import Log


class LogsRepository:
    def ensure_indexes(self):
        raise NotImplementedError

    def fetch_by_states_limit(self, states, limit) -> List[Log]:
        raise NotImplementedError

    def fetch_by_ids(self, migration_ids: List[int]) -> List[Log]:
        raise NotImplementedError

    def update(self, log: Log) -> bool:
        raise NotImplementedError

    def insert(self, log: Log):
        raise NotImplementedError
