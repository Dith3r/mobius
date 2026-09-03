from mobius.commands.difference import DifferenceCommand
from mobius.commons.data import file_md5
from mobius.commons.logger.model import Failed, InProgress, Log, Skipped, Succeed
from mobius.commons.logger.service import Logger
from tests.fakes import FakeLogsRepository


def write_migration(directory, migration_id):
    file = directory / f"{migration_id}.py"
    file.write_text(f"# migration {migration_id}\n")
    return file


def make_command():
    logs = FakeLogsRepository()
    return DifferenceCommand(Logger(logs)), logs


def record(logs, file, state):
    log = Log.new(int(file.stem), file_md5(file))
    log.state = state
    logs.insert(log)


def test_all_applied(tmp_path):
    command, logs = make_command()

    for migration_id, state in ((100, Succeed), (200, Skipped)):
        record(logs, write_migration(tmp_path, migration_id), state)

    assert command.execute(str(tmp_path)) == []


def test_reports_pending_and_incomplete_migrations(tmp_path):
    command, logs = make_command()

    record(logs, write_migration(tmp_path, 100), Succeed)
    record(logs, write_migration(tmp_path, 200), Failed)
    record(logs, write_migration(tmp_path, 300), InProgress)
    write_migration(tmp_path, 400)  # never run
    record(logs, write_migration(tmp_path, 500), Skipped)

    differences = command.execute(str(tmp_path))

    assert [(diff.name, diff.reason) for diff in differences] == [
        ("200.py", "state: Failed"),
        ("300.py", "state: InProgress"),
        ("400.py", "never run"),
    ]


def test_reports_applied_but_changed_file(tmp_path):
    command, logs = make_command()

    file = write_migration(tmp_path, 100)
    record(logs, file, Succeed)
    file.write_text(file.read_text() + "# changed\n")

    differences = command.execute(str(tmp_path))

    assert [(diff.name, diff.reason) for diff in differences] == [
        ("100.py", "applied but file changed"),
    ]


def test_ignores_non_python_files(tmp_path):
    command, _ = make_command()

    (tmp_path / "notes.txt").write_text("not a migration")

    assert command.execute(str(tmp_path)) == []
