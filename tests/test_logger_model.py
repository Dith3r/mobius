from mobius.commons.logger.model import (
    Failed,
    InProgress,
    Log,
    New,
    Skipped,
    Succeed,
    filename_to_id,
)


def test_filename_to_id():
    assert filename_to_id("172535000000.py") == 172535000000


def test_state_str_is_class_name():
    assert str(Succeed) == "Succeed"
    assert str(Failed) == "Failed"


def test_log_new_defaults():
    log = Log.new(123, "abc")

    assert log.id == 123
    assert log.hash == "abc"
    assert log.state is New
    assert log.msg is None
    assert log.created_at == log.updated_at


def test_states_are_distinct():
    states = {New, InProgress, Skipped, Succeed, Failed}
    assert len(states) == 5
