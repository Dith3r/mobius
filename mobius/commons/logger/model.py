import re
from datetime import datetime
from typing import Dict, Optional, Type


class Simple(type):
    def __str__(self):
        return self.__mro__[0].__name__


class State(metaclass=Simple):
    __slots__ = ()


class New(State):
    __slots__ = ()


class InProgress(State):
    __slots__ = ()


class Skipped(State):
    __slots__ = ()


class Succeed(State):
    __slots__ = ()


class Failed(State):
    __slots__ = ()


class Log:
    __slots__ = ("id", "created_at", "updated_at", "hash", "msg", "state")
    id: int
    created_at: datetime
    updated_at: datetime
    hash: str
    msg: Optional[str]
    state: Type[State]

    def __init__(
        self,
        id: int,
        created_at: datetime,
        updated_at: datetime,
        hash: str,
        state: Type[State],
        msg: Optional[str] = None,
    ):
        self.id = id
        self.state = state
        self.created_at = created_at
        self.updated_at = updated_at
        self.hash = hash
        self.msg = msg

    @classmethod
    def new(cls, log_id: int, hash: str, msg: Optional[str] = None):
        datetime_now = datetime.utcnow()

        return cls(log_id, datetime_now, datetime_now, hash, New, msg)


class StateCodec:
    """Single source of truth for the persisted one-letter state encoding —
    shared by every state-store backend. The letters are a wire format:
    never change them for existing states."""

    __slots__ = ()

    TO: Dict[Type[State], str] = {
        New: "N",
        InProgress: "I",
        Skipped: "S",
        Succeed: "O",
        Failed: "F",
    }
    FROM: Dict[str, Type[State]] = {value: key for key, value in TO.items()}


MIGRATION_FILENAME = re.compile(r"^\d+\.py$")


def is_migration_filename(filename: str) -> bool:
    return MIGRATION_FILENAME.match(filename) is not None


def filename_to_id(filename: str) -> int:
    return int(filename.split(".")[0])
