import re
from datetime import datetime
from typing import List
from uuid import UUID

from mobius.commons.locker.model import Lock
from mobius.commons.locker.repository import LocksRepository
from mobius.commons.repositories import UniqueViolationError


TABLE_NAME = re.compile(r"^[A-Za-z0-9_]+$")


class LockMySqlMapper:
    __slots__ = ()

    class Fields:
        __slots__ = ()
        ID = "id"
        VALID_TILL = "valid_till"
        TRANSACTION_ID = "tx_id"
        HOLDER_ID = "holder_id"

    @classmethod
    def to_row(cls, lock: Lock) -> dict:
        _ = cls.Fields

        # mysql-connector does not adapt UUID objects; store as CHAR(36)
        return {
            _.ID: str(lock.id),
            _.VALID_TILL: lock.valid_till,
            _.TRANSACTION_ID: str(lock.transaction_id),
            _.HOLDER_ID: str(lock.holder_id),
        }


class LocksMySqlRepository(LocksRepository):
    def __init__(self, connection, table: str = "locks"):
        if not TABLE_NAME.match(table):
            raise ValueError(f"Invalid table name: {table}")

        self.connection = connection
        self.table = table

    def _execute(self, query: str, params=None) -> int:
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            return cursor.rowcount
        finally:
            cursor.close()

    def ensure_indexes(self):
        self._execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{self.table}` (
                id CHAR(36) PRIMARY KEY,
                valid_till DATETIME(6) NOT NULL,
                tx_id CHAR(36) NOT NULL,
                holder_id CHAR(36) NOT NULL,
                INDEX tx_idx (tx_id)
            )
            """
        )

    def insert(self, lock: Lock):
        row = LockMySqlMapper.to_row(lock)
        row["now"] = datetime.utcnow()

        # assignments apply left to right, so the predicate column
        # (valid_till) must be assigned last
        affected = self._execute(
            f"""
            INSERT INTO `{self.table}` (id, valid_till, tx_id, holder_id)
            VALUES (%(id)s, %(valid_till)s, %(tx_id)s, %(holder_id)s)
            ON DUPLICATE KEY UPDATE
                tx_id = IF(valid_till < %(now)s, %(tx_id)s, tx_id),
                holder_id = IF(valid_till < %(now)s, %(holder_id)s, holder_id),
                valid_till = IF(valid_till < %(now)s, %(valid_till)s, valid_till)
            """,
            row,
        )

        # 1 = inserted, 2 = expired lock taken over, 0 = lock still held
        if affected == 0:
            raise UniqueViolationError(str(lock.id))

    def insert_many(self, locks: List[Lock]):
        duplicated = []

        for lock in locks:
            affected = self._execute(
                f"""
                INSERT IGNORE INTO `{self.table}` (id, valid_till, tx_id, holder_id)
                VALUES (%(id)s, %(valid_till)s, %(tx_id)s, %(holder_id)s)
                """,
                LockMySqlMapper.to_row(lock),
            )

            if affected == 0:
                duplicated.append(lock.id)

        if duplicated:
            raise UniqueViolationError(", ".join(str(id) for id in duplicated))

    def update_by_transaction_id(
        self, transaction_id: UUID, valid_till: datetime
    ) -> bool:
        affected = self._execute(
            f"UPDATE `{self.table}` SET valid_till = %s WHERE tx_id = %s",
            (valid_till, str(transaction_id)),
        )

        return affected == 1

    def delete_by_transaction_id(self, transaction_id: UUID):
        self._execute(
            f"DELETE FROM `{self.table}` WHERE tx_id = %s", (str(transaction_id),)
        )

    def delete_by_holder_id(self, holder_id: UUID):
        self._execute(
            f"DELETE FROM `{self.table}` WHERE holder_id = %s", (str(holder_id),)
        )
