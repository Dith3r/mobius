from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from mobius.commands.migrate import MigrateCommand
from mobius.commons.locker.model import Lock
from mobius.commons.locker.service import Locker
from mobius.commons.logger.model import Failed, Skipped, Succeed
from mobius.commons.logger.service import (
    Logger,
    NotCompletedMigrationsFoundException,
)
from mobius.config import MobiusSettings
from tests.fakes import FakeDriverManager, FakeLocksRepository, FakeLogsRepository


MIGRATION_OK = """
from pathlib import Path

from mobius import Migration


class Migration{mid}(Migration):
    def validate(self):
        pass

    def execute(self):
        Path(__file__).with_suffix(".done").write_text("done")

    def description(self):
        return "migration {mid}"
"""

MIGRATION_SKIPPED = """
from mobius import Migration, MigrationSkippedException


class Migration{mid}(Migration):
    def validate(self):
        pass

    def execute(self):
        raise MigrationSkippedException("not needed")

    def description(self):
        return "migration {mid}"
"""

MIGRATION_FAILED = """
from mobius import Migration, MigrationFailedException


class Migration{mid}(Migration):
    def validate(self):
        pass

    def execute(self):
        raise MigrationFailedException("boom")

    def description(self):
        return "migration {mid}"
"""


def write_migration(directory, migration_id, template):
    file = directory / f"{migration_id}.py"
    file.write_text(template.format(mid=migration_id))
    return file


def make_command():
    locks = FakeLocksRepository()
    logs = FakeLogsRepository()
    command = MigrateCommand(
        FakeDriverManager(), Logger(logs), Locker(locks), MobiusSettings()
    )
    return command, logs, locks


def test_migrations_run_in_order_and_states_recorded(tmp_path):
    write_migration(tmp_path, 100, MIGRATION_OK)
    write_migration(tmp_path, 200, MIGRATION_SKIPPED)

    command, logs, locks = make_command()
    command.execute(str(tmp_path), ignore_hash=False, no_wait=True)

    assert logs.logs[100].state is Succeed
    assert logs.logs[100].msg == "migration 100"
    assert logs.logs[200].state is Skipped
    assert logs.logs[200].msg == "not needed"
    assert (tmp_path / "100.done").exists()
    assert locks.locks == {}


def test_completed_migrations_are_not_rerun(tmp_path):
    write_migration(tmp_path, 100, MIGRATION_OK)

    command, logs, _ = make_command()
    command.execute(str(tmp_path), ignore_hash=False, no_wait=True)

    (tmp_path / "100.done").unlink()
    command.execute(str(tmp_path), ignore_hash=False, no_wait=True)

    assert not (tmp_path / "100.done").exists()
    assert logs.logs[100].state is Succeed


def test_failed_migration_stops_the_run(tmp_path):
    write_migration(tmp_path, 100, MIGRATION_FAILED)
    write_migration(tmp_path, 200, MIGRATION_OK)

    command, logs, locks = make_command()

    with pytest.raises(ValueError):
        command.execute(str(tmp_path), ignore_hash=False, no_wait=True)

    assert logs.logs[100].state is Failed
    assert logs.logs[100].msg == "boom"
    assert 200 not in logs.logs
    # lock is released even on failure
    assert locks.locks == {}


def test_failed_state_blocks_next_run(tmp_path):
    write_migration(tmp_path, 100, MIGRATION_FAILED)

    command, _, _ = make_command()

    with pytest.raises(ValueError):
        command.execute(str(tmp_path), ignore_hash=False, no_wait=True)

    with pytest.raises(NotCompletedMigrationsFoundException):
        command.execute(str(tmp_path), ignore_hash=False, no_wait=True)


def test_changed_hash_is_rejected(tmp_path):
    file = write_migration(tmp_path, 100, MIGRATION_OK)

    command, _, _ = make_command()
    command.execute(str(tmp_path), ignore_hash=False, no_wait=True)

    file.write_text(file.read_text() + "\n# changed\n")

    with pytest.raises(ValueError):
        command.execute(str(tmp_path), ignore_hash=False, no_wait=True)


def test_changed_hash_is_tolerated_with_ignore_hash(tmp_path):
    file = write_migration(tmp_path, 100, MIGRATION_OK)

    command, logs, _ = make_command()
    command.execute(str(tmp_path), ignore_hash=False, no_wait=True)

    file.write_text(file.read_text() + "\n# changed\n")
    command.execute(str(tmp_path), ignore_hash=True, no_wait=True)

    assert logs.logs[100].state is Succeed


def test_held_lock_with_no_wait_returns_without_running(tmp_path):
    write_migration(tmp_path, 100, MIGRATION_OK)

    command, logs, locks = make_command()
    locks.insert(
        Lock(
            MigrateCommand.GLOBAL_LOCK,
            datetime.utcnow() + timedelta(seconds=60),
            uuid4(),
            uuid4(),
        )
    )

    command.execute(str(tmp_path), ignore_hash=False, no_wait=True)

    assert logs.logs == {}
    assert not (tmp_path / "100.done").exists()
