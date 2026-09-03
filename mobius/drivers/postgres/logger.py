from typing import List, Type

from psycopg import Connection, sql
from psycopg.rows import dict_row

from mobius.commons.logger.model import Log, State, StateCodec
from mobius.commons.logger.repository import LogsRepository


class StatePostgresMapper:
    TO = StateCodec.TO
    FROM = StateCodec.FROM

    @classmethod
    def to_row(cls, state: Type[State]) -> str:
        return cls.TO[state]

    @classmethod
    def from_row(cls, raw: str):
        return cls.FROM[raw]


class LogPostgresMapper:
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
            _.STATE: StatePostgresMapper.to_row(log.state),
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
            state=StatePostgresMapper.from_row(data[_.STATE]),
        )


class LogsPostgresRepository(LogsRepository):
    def __init__(self, connection: Connection, table: str = "logs"):
        self.connection = connection
        self.connection.row_factory = dict_row
        self.table = sql.Identifier(table)

    def ensure_indexes(self):
        with self.connection.transaction():
            self.connection.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {table} (
                        id bigint PRIMARY KEY,
                        created_at timestamp NOT NULL,
                        updated_at timestamp NOT NULL,
                        hash text NOT NULL,
                        msg text,
                        state varchar(1) NOT NULL
                    )
                    """
                ).format(table=self.table)
            )
            self.connection.execute(
                sql.SQL(
                    "CREATE INDEX IF NOT EXISTS state_idx ON {table} (state)"
                ).format(table=self.table)
            )

    def fetch_by_states_limit(self, states, limit) -> List[Log]:
        raw_states = [StatePostgresMapper.to_row(state) for state in states]

        result = self.connection.execute(
            sql.SQL(
                """
                SELECT id, created_at, updated_at, hash, msg, state
                FROM {table}
                WHERE state = ANY(%s)
                ORDER BY id
                LIMIT %s
                """
            ).format(table=self.table),
            (raw_states, limit),
        )

        return [LogPostgresMapper.from_row(row) for row in result]

    def fetch_by_ids(self, migration_ids: List[int]) -> List[Log]:
        result = self.connection.execute(
            sql.SQL(
                """
                SELECT id, created_at, updated_at, hash, msg, state
                FROM {table}
                WHERE id = ANY(%s)
                """
            ).format(table=self.table),
            (migration_ids,),
        )

        return [LogPostgresMapper.from_row(row) for row in result]

    def update(self, log: Log) -> bool:
        row = LogPostgresMapper.to_row(log)

        with self.connection.transaction():
            result = self.connection.execute(
                sql.SQL(
                    """
                    UPDATE {table}
                    SET updated_at = %(updated_at)s,
                        hash = %(hash)s,
                        msg = %(msg)s,
                        state = %(state)s
                    WHERE id = %(id)s
                    """
                ).format(table=self.table),
                row,
            )

        return result.rowcount == 1

    def insert(self, log: Log):
        row = LogPostgresMapper.to_row(log)

        with self.connection.transaction():
            self.connection.execute(
                sql.SQL(
                    """
                    INSERT INTO {table} (id, created_at, updated_at, hash, msg, state)
                    VALUES (%(id)s, %(created_at)s, %(updated_at)s, %(hash)s, %(msg)s, %(state)s)
                    """
                ).format(table=self.table),
                row,
            )
