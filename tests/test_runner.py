import queue

import pytest

from mobius.migration.runner import (
    FailedResult,
    SkippedResult,
    SuccessResult,
    migration_handler,
)


MIGRATION_OK = """
from mobius import Migration


class Migration100(Migration):
    def validate(self):
        pass

    def execute(self):
        pass

    def description(self):
        return "all good"
"""

MIGRATION_SKIPPED = """
from mobius import Migration, MigrationSkippedException


class Migration200(Migration):
    def validate(self):
        pass

    def execute(self):
        raise MigrationSkippedException("not needed")

    def description(self):
        return "skipped one"
"""

MIGRATION_FAILED = """
from mobius import Migration, MigrationFailedException


class Migration300(Migration):
    def validate(self):
        pass

    def execute(self):
        raise MigrationFailedException("boom")

    def description(self):
        return "failing one"
"""

MIGRATION_CRASH = """
from mobius import Migration


class Migration400(Migration):
    def validate(self):
        pass

    def execute(self):
        raise RuntimeError("unexpected")

    def description(self):
        return "crashing one"
"""


def run_handler(tmp_path, migration_id, source):
    file = tmp_path / f"{migration_id}.py"
    file.write_text(source)

    results = queue.Queue()
    migration_handler({}, migration_id, file.name, str(file), results, 20)
    return results.get(block=False)


def test_successful_migration(tmp_path):
    result = run_handler(tmp_path, "100", MIGRATION_OK)

    assert isinstance(result, SuccessResult)
    assert result.msg == "all good"


def test_skipped_migration(tmp_path):
    result = run_handler(tmp_path, "200", MIGRATION_SKIPPED)

    assert isinstance(result, SkippedResult)
    assert result.msg == "not needed"


def test_failed_migration(tmp_path):
    result = run_handler(tmp_path, "300", MIGRATION_FAILED)

    assert isinstance(result, FailedResult)
    assert result.msg == "boom"
    assert result.trace


def test_unhandled_exception_exits_and_reports(tmp_path):
    file = tmp_path / "400.py"
    file.write_text(MIGRATION_CRASH)

    results = queue.Queue()

    with pytest.raises(SystemExit):
        migration_handler({}, "400", file.name, str(file), results, 20)

    result = results.get(block=False)
    assert isinstance(result, FailedResult)
    assert "unexpected" in result.msg
