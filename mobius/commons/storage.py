from datetime import datetime
from typing import Optional
from uuid import (
    UUID,
    uuid4,
)


class Log:
    __slots__ = ('id', 'at', 'name', 'hash', 'msg')
    id: UUID
    at: datetime
    name: str
    hash: str
    msg: Optional[str]

    def __init__(self,
                 id: UUID,
                 at: datetime,
                 name: str,
                 hash: str,
                 msg: Optional[str] = None):
        self.id = id
        self.at = at
        self.name = name
        self.hash = hash
        self.msg = msg

    @classmethod
    def new(cls,
            name: str,
            hash: str,
            msg: Optional[str] = None):
        id = uuid4()
        at = datetime.utcnow()

        return cls(id,
                   at,
                   name,
                   hash,
                   msg)
