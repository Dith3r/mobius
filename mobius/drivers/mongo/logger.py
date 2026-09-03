from typing import List, Type

import pymongo
from pymongo import IndexModel, MongoClient

from mobius.commons.logger.model import Log, State, StateCodec
from mobius.commons.logger.repository import LogsRepository


class StateMongoMapper:
    TO = StateCodec.TO
    FROM = StateCodec.FROM

    @classmethod
    def to_mongo(cls, state: Type[State]) -> str:
        return cls.TO[state]

    @classmethod
    def from_mongo(cls, raw: str):
        return cls.FROM[raw]


class LogMongoMapper:
    __slots__ = ()

    class Fields:
        __slots__ = ()
        ID = "_id"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"
        HASH = "hash"
        MSG = "msg"
        STATE = "state"

    @classmethod
    def to_mongo(cls, log: Log, created: bool = False) -> dict:
        _ = cls.Fields

        result = {
            _.ID: log.id,
            _.UPDATED_AT: log.updated_at,
            _.HASH: log.hash,
            _.MSG: log.msg,
            _.STATE: StateMongoMapper.to_mongo(log.state),
        }

        if created:
            result.update({_.CREATED_AT: log.created_at})

        return result

    @classmethod
    def from_mongo(cls, data: dict) -> Log:
        _ = cls.Fields

        return Log(
            id=data[_.ID],
            created_at=data[_.CREATED_AT],
            updated_at=data[_.UPDATED_AT],
            hash=data[_.HASH],
            msg=data.get(_.MSG),
            state=StateMongoMapper.from_mongo(data[_.STATE]),
        )


class LogsMongoRepository(LogsRepository):
    client: MongoClient

    def __init__(self, client: MongoClient, collection: str = "logs"):
        self.client = client
        self.collection_name = collection
        self.collection = self.client.get_default_database().get_collection(collection)

    def ensure_indexes(self):
        _ = LogMongoMapper.Fields

        self.collection.create_indexes(
            [
                IndexModel(
                    [(_.STATE, pymongo.ASCENDING)],
                    name="state_idx",
                )
            ]
        )

    def fetch_by_states_limit(self, states, limit) -> List[Log]:
        _ = LogMongoMapper.Fields

        query = {
            _.STATE: {"$in": [StateMongoMapper.to_mongo(state) for state in states]}
        }

        result = [
            LogMongoMapper.from_mongo(row)
            for row in self.collection.find(
                query, limit=limit, sort=[(_.ID, pymongo.ASCENDING)]
            )
        ]

        return result

    def fetch_by_ids(self, migration_ids: List[int]) -> List[Log]:
        _ = LogMongoMapper.Fields

        query = {_.ID: {"$in": migration_ids}}

        result = [LogMongoMapper.from_mongo(row) for row in self.collection.find(query)]

        return result

    def update(self, log: Log) -> bool:
        _ = LogMongoMapper.Fields

        query = {
            _.ID: log.id,
        }

        update = {"$set": LogMongoMapper.to_mongo(log)}

        return self.collection.update_one(query, update).modified_count == 1

    def insert(self, log: Log):
        data = LogMongoMapper.to_mongo(log, created=True)

        self.collection.insert_one(data)
