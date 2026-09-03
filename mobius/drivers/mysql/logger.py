import re
from typing import Dict, List, Type

from pymysql.cursors import DictCursor
from pymysql.err import IntegrityError

from mobius.commons.data import reverse_map
from mobius.commons.logger.model import (
    Failed,
    InProgress,
    Log,
    New,
    Skipped,
    State,
    Succeed,
)
from mobius.commons.logger.repository import LogsRepository
from mobius.commons.repositories import UniqueViolationError


TABLE_NAME = re.compile(r"^[A-Za-z0-9_]+$")


class StateMySqlMapper:
    TO: Dict[Type[State], str] = {
        New: "N",
        InProgress: "I",
        Skipped: "S",
        Succeed: "O",
        Failed: "F",
    }
    FROM = reverse_map(TO)

    @classmethod
    def to_row(cls, state: Type[State]) -> str:
        return cls.TO[state]

    @classmethod
    def from_row(cls, raw: str):
        return cls.FROM[raw]


class LogMySqlMapper:
    __slots__ = ()

    class Fields:
        __slots__ = ()
        ID = "id"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"
        HASH = "hash"
        MSG = "msg"
        STATE = "state"

    @classmethod
    def to_row(cls, log: Log) -> dict:
        _ = cls.Fields

        return {
            _.ID: log.id,
            _.CREATED_AT: log.created_at,
            _.UPDATED_AT: log.updated_at,
            _.HASH: log.hash,
            _.MSG: log.msg,
            _.STATE: StateMySqlMapper.to_row(log.state),
        }

    @classmethod
    def from_row(cls, data: dict) -> Log:
        _ = cls.Fields

        return Log(
            id=data[_.ID],
            created_at=data[_.CREATED_AT],
            updated_at=data[_.UPDATED_AT],
            hash=data[_.HASH],
            msg=data[_.MSG],
            state=StateMySqlMapper.from_row(data[_.STATE]),
        )


class LogsMySqlRepository(LogsRepository):
    def __init__(self, connection, table: str = "logs"):
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

    def _fetch(self, query: str, params=None) -> List[dict]:
        cursor = self.connection.cursor(DictCursor)
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()

    def ensure_indexes(self):
        self._execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{self.table}` (
                id BIGINT PRIMARY KEY,
                created_at DATETIME(6) NOT NULL,
                updated_at DATETIME(6) NOT NULL,
                hash VARCHAR(64) NOT NULL,
                msg TEXT,
                state CHAR(1) NOT NULL,
                INDEX state_idx (state)
            )
            """
        )

    def fetch_by_states_limit(self, states, limit) -> List[Log]:
        placeholders = ", ".join(["%s"] * len(states))

        rows = self._fetch(
            f"""
            SELECT id, created_at, updated_at, hash, msg, state
            FROM `{self.table}`
            WHERE state IN ({placeholders})
            ORDER BY id
            LIMIT %s
            """,
            [StateMySqlMapper.to_row(state) for state in states] + [limit],
        )

        return [LogMySqlMapper.from_row(row) for row in rows]

    def fetch_by_ids(self, migration_ids: List[int]) -> List[Log]:
        if not migration_ids:
            return []

        placeholders = ", ".join(["%s"] * len(migration_ids))

        rows = self._fetch(
            f"""
            SELECT id, created_at, updated_at, hash, msg, state
            FROM `{self.table}`
            WHERE id IN ({placeholders})
            """,
            migration_ids,
        )

        return [LogMySqlMapper.from_row(row) for row in rows]

    def update(self, log: Log) -> bool:
        affected = self._execute(
            f"""
            UPDATE `{self.table}`
            SET updated_at = %(updated_at)s,
                hash = %(hash)s,
                msg = %(msg)s,
                state = %(state)s
            WHERE id = %(id)s
            """,
            LogMySqlMapper.to_row(log),
        )

        return affected == 1

    def insert(self, log: Log):
        try:
            self._execute(
                f"""
                INSERT INTO `{self.table}` (id, created_at, updated_at, hash, msg, state)
                VALUES (%(id)s, %(created_at)s, %(updated_at)s, %(hash)s, %(msg)s, %(state)s)
                """,
                LogMySqlMapper.to_row(log),
            )
        except IntegrityError:
            raise UniqueViolationError(str(log.id))
