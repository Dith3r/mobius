from datetime import datetime, timedelta
from uuid import uuid4

import pytest

pymongo = pytest.importorskip("pymongo")

from mobius.commons.locker.model import Lock  # noqa: E402
from mobius.commons.logger.model import Failed, InProgress, Log, Succeed  # noqa: E402
from mobius.commons.repositories import UniqueViolationError  # noqa: E402
from mobius.drivers.mongo.locker import LocksMongoRepository  # noqa: E402
from mobius.drivers.mongo.logger import LogsMongoRepository  # noqa: E402


LOCK_ID = uuid4()


@pytest.fixture(scope="module")
def client(mongo_url):
    client = pymongo.MongoClient(mongo_url, uuidRepresentation="standard")
    yield client
    client.close()


@pytest.fixture()
def locks(client):
    repository = LocksMongoRepository(client)
    repository.ensure_indexes()
    repository.collection.delete_many({})
    return repository


@pytest.fixture()
def logs(client):
    repository = LogsMongoRepository(client)
    repository.ensure_indexes()
    repository.collection.delete_many({})
    return repository


def make_lock():
    return Lock(LOCK_ID, datetime.utcnow() + timedelta(seconds=60), uuid4(), uuid4())


def test_lock_acquired_then_conflicts(locks):
    locks.insert(make_lock())

    with pytest.raises(UniqueViolationError):
        locks.insert(make_lock())


def test_heartbeat_updates_lock_date(locks):
    lock = make_lock()
    locks.insert(lock)

    assert locks.update_by_transaction_id(
        lock.transaction_id, datetime.utcnow() + timedelta(seconds=300)
    )
    assert not locks.update_by_transaction_id(uuid4(), datetime.utcnow())


def test_delete_by_transaction_id(locks):
    lock = make_lock()
    locks.insert(lock)

    locks.delete_by_transaction_id(lock.transaction_id)

    assert locks.collection.count_documents({}) == 0


def make_log(log_id, state, msg=None):
    log = Log.new(log_id, f"hash-{log_id}", msg)
    log.state = state
    return log


def test_log_round_trip(logs):
    logs.insert(make_log(100, Succeed, "done"))

    fetched = logs.fetch_by_ids([100])

    assert len(fetched) == 1
    assert fetched[0].id == 100
    assert fetched[0].hash == "hash-100"
    assert fetched[0].msg == "done"
    assert fetched[0].state is Succeed


def test_log_update(logs):
    log = make_log(100, InProgress)
    logs.insert(log)

    log.state = Failed
    log.msg = "boom"
    assert logs.update(log)

    fetched = logs.fetch_by_ids([100])[0]
    assert fetched.state is Failed
    assert fetched.msg == "boom"


def test_fetch_by_states_orders_and_limits(logs):
    logs.insert(make_log(300, Failed))
    logs.insert(make_log(100, Failed))
    logs.insert(make_log(200, Succeed))

    fetched = logs.fetch_by_states_limit([Failed, InProgress], limit=1)

    assert [log.id for log in fetched] == [100]
