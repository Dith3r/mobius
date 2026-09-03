import time
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from mobius.commons.locker.model import Lock, LockFailedException, LockLostException
from mobius.commons.locker.service import Locker
from mobius.commons.repositories import UniqueViolationError
from tests.fakes import FakeLocksRepository


LOCK_ID = uuid4()


def wait_until(condition, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return False


def test_lock_acquire_and_release():
    repository = FakeLocksRepository()
    locker = Locker(repository)

    with locker.lock(LOCK_ID, uuid4(), ttl=90) as handle:
        assert not handle.lost
        handle.ensure_valid()
        assert LOCK_ID in repository.locks

    assert repository.locks == {}


def test_lock_already_held_raises_lock_failed():
    repository = FakeLocksRepository()
    repository.insert(
        Lock(LOCK_ID, datetime.utcnow() + timedelta(seconds=60), uuid4(), uuid4())
    )
    locker = Locker(repository)

    with pytest.raises(LockFailedException):
        with locker.lock(LOCK_ID, uuid4(), ttl=90):
            pass

    # the foreign lock must not be deleted by the failed attempt
    assert LOCK_ID in repository.locks


def test_lock_failure_does_not_swallow_body_unique_violations():
    repository = FakeLocksRepository()
    locker = Locker(repository)

    with pytest.raises(UniqueViolationError):
        with locker.lock(LOCK_ID, uuid4(), ttl=90):
            raise UniqueViolationError("some_index")


def test_heartbeat_renews_ttl():
    repository = FakeLocksRepository()
    locker = Locker(repository)

    # ttl=1 -> heartbeat every ~1s
    with locker.lock(LOCK_ID, uuid4(), ttl=1) as handle:
        assert wait_until(lambda: repository.update_calls >= 1)
        assert not handle.lost

    assert repository.locks == {}


def test_lock_lost_sets_handle_and_ensure_valid_raises():
    repository = FakeLocksRepository()
    repository.fail_updates = True
    locker = Locker(repository)

    with locker.lock(LOCK_ID, uuid4(), ttl=1) as handle:
        assert wait_until(lambda: handle.lost)

        with pytest.raises(LockLostException):
            handle.ensure_valid()


def test_repository_error_in_heartbeat_marks_lock_lost():
    repository = FakeLocksRepository()
    repository.raise_on_update = True
    locker = Locker(repository)

    with locker.lock(LOCK_ID, uuid4(), ttl=1) as handle:
        assert wait_until(lambda: handle.lost)
