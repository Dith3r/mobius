from datetime import datetime, timedelta
from uuid import uuid4

import pytest

pymysql = pytest.importorskip("pymysql")

from mobius.commons.locker.model import Lock, LockFailedException  # noqa: E402
from mobius.commons.locker.service import Locker  # noqa: E402
from mobius.commons.logger.model import Failed, InProgress, Log, Succeed  # noqa: E402
from mobius.commons.repositories import UniqueViolationError  # noqa: E402
from mobius.drivers.mysql.config import MysqlConfigDriver  # noqa: E402
from mobius.drivers.mysql.driver import MySqlDriver  # noqa: E402


LOCK_ID = uuid4()


@pytest.fixture()
def driver(mysql_config):
    return MySqlDriver("state", MysqlConfigDriver(**mysql_config))


@pytest.fixture()
def locks(driver):
    repository = driver.get_locks_repository()
    repository.ensure_indexes()
    repository._execute("DELETE FROM locks")
    yield repository
    repository.connection.close()


@pytest.fixture()
def logs(driver):
    repository = driver.get_logs_repository()
    repository.ensure_indexes()
    repository._execute("DELETE FROM logs")
    yield repository
    repository.connection.close()


def make_lock(valid_till=None):
    valid_till = valid_till or datetime.utcnow() + timedelta(seconds=60)
    return Lock(LOCK_ID, valid_till, uuid4(), uuid4())


def fetch_lock_row(locks):
    cursor = locks.connection.cursor()
    try:
        cursor.execute(
            "SELECT tx_id, holder_id FROM locks WHERE id = %s", (str(LOCK_ID),)
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def test_lock_acquired_then_conflicts(locks):
    locks.insert(make_lock())

    with pytest.raises(UniqueViolationError):
        locks.insert(make_lock())


def test_expired_lock_is_taken_over(locks):
    stale = make_lock(valid_till=datetime.utcnow() - timedelta(seconds=1))
    locks.insert(stale)

    fresh = make_lock()
    locks.insert(fresh)  # must not raise: date has passed, row is taken over

    row = fetch_lock_row(locks)
    assert row == (str(fresh.transaction_id), str(fresh.holder_id))


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

    assert fetch_lock_row(locks) is None


def test_locker_service_end_to_end(driver, locks):
    second_repository = driver.get_locks_repository()

    with Locker(locks).lock(LOCK_ID, uuid4(), ttl=90) as handle:
        assert not handle.lost

        with pytest.raises(LockFailedException):
            with Locker(second_repository).lock(LOCK_ID, uuid4(), ttl=90):
                pass

    # released: acquirable again
    with Locker(second_repository).lock(LOCK_ID, uuid4(), ttl=90):
        pass

    second_repository.connection.close()


def make_log(log_id, state, msg=None):
    log = Log.new(log_id, f"hash-{log_id}", msg)
    log.state = state
    return log


def test_log_round_trip(logs):
    log = make_log(100, Succeed, "done")
    logs.insert(log)

    fetched = logs.fetch_by_ids([100])

    assert len(fetched) == 1
    assert fetched[0].id == 100
    assert fetched[0].hash == "hash-100"
    assert fetched[0].msg == "done"
    assert fetched[0].state is Succeed
    assert fetched[0].created_at == log.created_at


def test_duplicate_log_insert_raises(logs):
    logs.insert(make_log(100, Succeed))

    with pytest.raises(UniqueViolationError):
        logs.insert(make_log(100, Succeed))


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
