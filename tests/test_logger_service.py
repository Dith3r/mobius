import pytest

from mobius.commons.logger.model import Failed, InProgress, Log, Succeed
from mobius.commons.logger.service import (
    Logger,
    NotCompletedMigrationsFoundException,
)
from tests.fakes import FakeLogsRepository


def make_log(log_id, state):
    log = Log.new(log_id, f"hash-{log_id}")
    log.state = state
    return log


def test_ensure_all_completed_passes_when_clean():
    repository = FakeLogsRepository()
    repository.insert(make_log(1, Succeed))

    Logger(repository).ensure_all_completed()


@pytest.mark.parametrize("state", [Failed, InProgress])
def test_ensure_all_completed_raises_on_unfinished(state):
    repository = FakeLogsRepository()
    repository.insert(make_log(1, Succeed))
    repository.insert(make_log(2, state))

    with pytest.raises(NotCompletedMigrationsFoundException) as info:
        Logger(repository).ensure_all_completed()

    assert info.value.log.id == 2


def test_update_bumps_updated_at():
    repository = FakeLogsRepository()
    log = make_log(1, Succeed)
    repository.insert(log)

    before = log.updated_at
    Logger(repository).update(log)

    assert repository.logs[1].updated_at >= before


def test_fetch_by_id():
    repository = FakeLogsRepository()
    repository.insert(make_log(1, Succeed))
    repository.insert(make_log(2, Failed))

    logs = Logger(repository).fetch_by_id([1, 2, 3])

    assert sorted(log.id for log in logs) == [1, 2]
