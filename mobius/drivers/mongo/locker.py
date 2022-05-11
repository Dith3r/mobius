from datetime import datetime
from typing import List
from uuid import UUID

import pymongo
from pymongo import IndexModel, MongoClient
from pymongo.errors import BulkWriteError, DuplicateKeyError

from mobius.commons.locker.model import Lock
from mobius.commons.locker.repository import LocksRepository
from mobius.commons.repositories import UniqueViolationError
from mobius.drivers.mongo.utils import Mongo


class InsertManyIdException(Exception):
    CODE_DUPLICATION = 11000

    def __init__(self, duplicated_ids):
        self.duplicated_ids = duplicated_ids

    @classmethod
    def from_bulk_write(cls, bulk_write: BulkWriteError):
        write_errors = bulk_write.details["writeErrors"]
        duplicated = []

        for error in write_errors:
            if error["code"] == cls.CODE_DUPLICATION:
                duplicated.append(error["op"]["_id"])

        return InsertManyIdException(duplicated)


class LockMongoMapper:
    __slots__ = ()

    class Fields:
        __slots__ = ()
        ID = "_id"
        VALID_TILL = "valid_till"
        TRANSACTION_ID = "tx_id"
        HOLDER_ID = "holder_id"

    @classmethod
    def to_mongo(cls, lock: Lock) -> dict:
        _ = cls.Fields

        return {
            _.ID: lock.id,
            _.VALID_TILL: lock.valid_till,
            _.TRANSACTION_ID: lock.transaction_id,
            _.HOLDER_ID: lock.holder_id,
        }


class LocksMongoRepository(LocksRepository):
    def __init__(self, client: MongoClient, collection: str = "locks"):
        self.client = client
        self.collection = self.client.get_default_database().get_collection(collection)

    def insert(self, lock: Lock):
        try:
            data = LockMongoMapper.to_mongo(lock)
            self.collection.insert_one(data)

        except DuplicateKeyError as exception:
            raise UniqueViolationError(Mongo.extract_unique_violation(exception))

    def update_by_transaction_id(
        self, transaction_id: UUID, valid_till: datetime
    ) -> bool:
        _ = LockMongoMapper.Fields

        query = {_.TRANSACTION_ID: transaction_id}
        update = {"$set": {_.VALID_TILL: valid_till}}

        return self.collection.update_one(query, update).modified_count == 1

    def insert_many(self, locks: List[Lock]):
        try:
            data = [LockMongoMapper.to_mongo(row) for row in locks]
            self.collection.insert_many(data, ordered=False)
        except BulkWriteError as exception:
            raise InsertManyIdException.from_bulk_write(exception)

    def delete_by_transaction_id(self, transaction_id: UUID):
        _ = LockMongoMapper.Fields

        query = {_.TRANSACTION_ID: transaction_id}

        self.collection.delete_many(query)

    def delete_by_holder_id(self, holder_id: UUID):
        _ = LockMongoMapper.Fields

        query = {_.HOLDER_ID: holder_id}

        self.collection.delete_many(query)

    def ensure_indexes(self):
        _ = LockMongoMapper.Fields

        self.collection.create_indexes(
            [
                IndexModel(
                    [(_.VALID_TILL, pymongo.ASCENDING)],
                    name="till_idx",
                    expireAfterSeconds=0,
                ),
                IndexModel(
                    [(_.TRANSACTION_ID, pymongo.ASCENDING)],
                    name="tx_idx",
                ),
            ]
        )
