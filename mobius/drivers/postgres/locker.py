from datetime import datetime
from typing import List
from uuid import UUID

from psycopg import Connection, sql

from mobius.commons.locker.model import Lock
from mobius.commons.locker.repository import LocksRepository
from mobius.commons.repositories import UniqueViolationError


class LockPostgresMapper:
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

        return {
            _.ID: lock.id,
            _.VALID_TILL: lock.valid_till,
            _.TRANSACTION_ID: lock.transaction_id,
            _.HOLDER_ID: lock.holder_id,
        }


class LocksPostgresRepository(LocksRepository):
    def __init__(self, connection: Connection, table: str = "locks"):
        self.connection = connection
        self.table = sql.Identifier(table)

    def ensure_indexes(self):
        with self.connection.transaction():
            self.connection.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {table} (
                        id uuid PRIMARY KEY,
                        valid_till timestamp NOT NULL,
                        tx_id uuid NOT NULL,
                        holder_id uuid NOT NULL
                    )
                    """
                ).format(table=self.table)
            )
            self.connection.execute(
                sql.SQL(
                    "CREATE INDEX IF NOT EXISTS tx_idx ON {table} (tx_id)"
                ).format(table=self.table)
            )

    def insert(self, lock: Lock):
        row = LockPostgresMapper.to_row(lock)
        row["now"] = datetime.utcnow()

        with self.connection.transaction():
            result = self.connection.execute(
                sql.SQL(
                    """
                    INSERT INTO {table} (id, valid_till, tx_id, holder_id)
                    VALUES (%(id)s, %(valid_till)s, %(tx_id)s, %(holder_id)s)
                    ON CONFLICT (id) DO UPDATE
                        SET valid_till = EXCLUDED.valid_till,
                            tx_id = EXCLUDED.tx_id,
                            holder_id = EXCLUDED.holder_id
                        WHERE {table}.valid_till < %(now)s
                    RETURNING id
                    """
                ).format(table=self.table),
                row,
            ).fetchone()

        if result is None:
            raise UniqueViolationError(f"{lock.id}")

    def insert_many(self, locks: List[Lock]):
        duplicated = []

        with self.connection.transaction():
            for lock in locks:
                result = self.connection.execute(
                    sql.SQL(
                        """
                        INSERT INTO {table} (id, valid_till, tx_id, holder_id)
                        VALUES (%(id)s, %(valid_till)s, %(tx_id)s, %(holder_id)s)
                        ON CONFLICT (id) DO NOTHING
                        RETURNING id
                        """
                    ).format(table=self.table),
                    LockPostgresMapper.to_row(lock),
                ).fetchone()

                if result is None:
                    duplicated.append(lock.id)

        if duplicated:
            raise UniqueViolationError(", ".join(str(id) for id in duplicated))

    def update_by_transaction_id(
        self, transaction_id: UUID, valid_till: datetime
    ) -> bool:
        with self.connection.transaction():
            result = self.connection.execute(
                sql.SQL(
                    "UPDATE {table} SET valid_till = %s WHERE tx_id = %s"
                ).format(table=self.table),
                (valid_till, transaction_id),
            )

        return result.rowcount == 1

    def delete_by_transaction_id(self, transaction_id: UUID):
        with self.connection.transaction():
            self.connection.execute(
                sql.SQL("DELETE FROM {table} WHERE tx_id = %s").format(
                    table=self.table
                ),
                (transaction_id,),
            )

    def delete_by_holder_id(self, holder_id: UUID):
        with self.connection.transaction():
            self.connection.execute(
                sql.SQL("DELETE FROM {table} WHERE holder_id = %s").format(
                    table=self.table
                ),
                (holder_id,),
            )
