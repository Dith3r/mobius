from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from mobius.commons.locker.model import Lock, LockFailedException
from mobius.commons.locker.service import Locker
from mobius.commons.logger.model import Failed, InProgress, Log, Succeed
from mobius.commons.repositories import UniqueViolationError
from mobius.drivers.postgres.driver import PostgresDriver


LOCK_ID = uuid4()


@pytest.fixture()
def driver(postgres_url):
    return PostgresDriver("state", postgres_url, connect_timeout=10, autocommit=False)


@pytest.fixture()
def locks(driver):
    repository = driver.get_locks_repository()
    repository.ensure_indexes()
    repository.connection.execute("DELETE FROM locks")
    yield repository
    repository.connection.close()


@pytest.fixture()
def logs(driver):
    repository = driver.get_logs_repository()
    repository.ensure_indexes()
    repository.connection.execute("DELETE FROM logs")
    yield repository
    repository.connection.close()


def make_lock(valid_till=None):
    valid_till = valid_till or datetime.utcnow() + timedelta(seconds=60)
    return Lock(LOCK_ID, valid_till, uuid4(), uuid4())


def test_lock_acquired_then_conflicts(locks):
    locks.insert(make_lock())

    with pytest.raises(UniqueViolationError):
        locks.insert(make_lock())


def test_expired_lock_is_taken_over(locks):
    stale = make_lock(valid_till=datetime.utcnow() - timedelta(seconds=1))
    locks.insert(stale)

    fresh = make_lock()
    locks.insert(fresh)  # must not raise: date has passed, row is taken over

    row = locks.connection.execute(
        "SELECT tx_id, holder_id FROM locks WHERE id = %s", (LOCK_ID,)
    ).fetchone()
    assert row == (fresh.transaction_id, fresh.holder_id)


def test_heartbeat_updates_lock_date(locks):
    lock = make_lock()
    locks.insert(lock)

    new_valid_till = datetime.utcnow() + timedelta(seconds=300)
    assert locks.update_by_transaction_id(lock.transaction_id, new_valid_till)

    row = locks.connection.execute(
        "SELECT valid_till FROM locks WHERE id = %s", (LOCK_ID,)
    ).fetchone()
    assert row[0] == new_valid_till


def test_heartbeat_fails_for_unknown_transaction(locks):
    locks.insert(make_lock())

    assert not locks.update_by_transaction_id(uuid4(), datetime.utcnow())


def test_delete_by_transaction_id(locks):
    lock = make_lock()
    locks.insert(lock)

    locks.delete_by_transaction_id(lock.transaction_id)

    assert (
        locks.connection.execute("SELECT count(*) FROM locks").fetchone()[0] == 0
    )


def test_locker_service_end_to_end(postgres_url, locks, driver):
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


def test_log_update(logs):
    log = make_log(100, InProgress)
    logs.insert(log)

    log.state = Failed
    log.msg = "boom"
    assert logs.update(log)

    fetched = logs.fetch_by_ids([100])[0]
    assert fetched.state is Failed
    assert fetched.msg == "boom"


def test_update_unknown_log_returns_false(logs):
    assert not logs.update(make_log(999, Succeed))


def test_fetch_by_states_orders_and_limits(logs):
    logs.insert(make_log(300, Failed))
    logs.insert(make_log(100, Failed))
    logs.insert(make_log(200, Succeed))

    fetched = logs.fetch_by_states_limit([Failed, InProgress], limit=1)

    assert [log.id for log in fetched] == [100]
