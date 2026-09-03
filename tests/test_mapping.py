import pytest

from mobius.commons.mapping import (
    Checked,
    ErrorSink,
    InvalidValueError,
    MappingException,
    ObjectContext,
    Segment,
    map_object,
)


def read_noop(context: ObjectContext):
    return None


def test_segment_renders_dollar_rooted_dotted():
    segment = Segment().push("sources").push("db").push("connectionUrl")

    assert str(segment) == "$.sources.db.connectionUrl"
    assert segment == Segment(("sources", "db", "connectionUrl"))


def test_map_object_success():
    result = map_object({"name": "mobius"}, lambda ctx: ctx.get_string("name").or_none())

    assert result == "mobius"


def test_non_object_input_raises():
    with pytest.raises(MappingException):
        map_object("not-a-dict", read_noop)


def test_errors_accumulate_across_fields():
    def read(ctx: ObjectContext):
        ctx.get_string("missing")
        ctx.get_int("wrong_type")
        ctx.get_bool("null_value")
        return None

    data = {"wrong_type": "text", "null_value": None}

    with pytest.raises(MappingException) as info:
        map_object(data, read)

    errors = {str(segment): str(error) for segment, error in info.value.errors.items()}
    assert errors == {
        "$.missing": "VALIDATION.REQUIRED_KEY_MISSING",
        "$.wrong_type": "VALIDATION.INVALID_TYPE(type=Int)",
        "$.null_value": "VALIDATION.NULL_VALUE",
    }


def test_nested_object_errors_carry_full_segment():
    def read(ctx: ObjectContext):
        return ctx.get_object(
            "outer", lambda outer: outer.get_object(
                "inner", lambda inner: inner.get_string("value").or_none()
            ).or_none()
        ).or_none()

    with pytest.raises(MappingException) as info:
        map_object({"outer": {"inner": {}}}, read)

    assert [str(segment) for segment in info.value.errors] == ["$.outer.inner.value"]


def test_find_tolerates_missing_and_null():
    def read(ctx: ObjectContext):
        assert ctx.find_string("missing").or_none() is None
        assert ctx.find_string("null").or_none() is None
        assert ctx.find_int("present").or_else(5) == 7
        return "ok"

    assert map_object({"null": None, "present": 7}, read) == "ok"


def test_bool_is_not_an_int():
    def read(ctx: ObjectContext):
        ctx.get_int("flag")
        return None

    with pytest.raises(MappingException):
        map_object({"flag": True}, read)


def test_float_accepts_int():
    result = map_object(
        {"interval": 2}, lambda ctx: ctx.find_float("interval").or_none()
    )

    assert result == 2.0


def test_must_reports_at_field_segment():
    def read(ctx: ObjectContext):
        ctx.get_int("ttl").must(InvalidValueError(reason="positive"), lambda v: v > 0)
        return None

    with pytest.raises(MappingException) as info:
        map_object({"ttl": -1}, read)

    (segment,) = info.value.errors
    assert str(segment) == "$.ttl"


def test_try_map_reports_on_throw():
    def read(ctx: ObjectContext):
        return ctx.get_string("id").try_map(
            lambda value: InvalidValueError(param=value), int
        ).or_none()

    assert map_object({"id": "42"}, read) == 42

    with pytest.raises(MappingException):
        map_object({"id": "nope"}, read)


def test_construct_gates_on_errors_and_require_is_safe_inside():
    def read(ctx: ObjectContext):
        name = ctx.get_string("name")
        return ctx.construct(lambda: name.require().upper())

    assert map_object({"name": "mobius"}, read) == "MOBIUS"

    with pytest.raises(MappingException):
        map_object({}, read)


def test_require_outside_construct_raises_assertion():
    sink = ErrorSink()
    checked = Checked(None, Segment(("field",)), sink)

    with pytest.raises(AssertionError):
        checked.require()


def test_string_map_rejects_non_string_values():
    def read(ctx: ObjectContext):
        ctx.find_string_map("properties")
        return None

    with pytest.raises(MappingException):
        map_object({"properties": {"user": 42}}, read)


def test_max_errors_caps_collection():
    def read(ctx: ObjectContext):
        for index in range(20):
            ctx.get_string(f"field{index}")
        return None

    with pytest.raises(MappingException) as info:
        map_object({}, read, max_errors=3)

    assert len(info.value.errors) == 3


def test_first_error_per_segment_wins():
    sink = ErrorSink()
    segment = Segment(("field",))

    sink.report(segment, InvalidValueError(reason="first"))
    sink.report(segment, InvalidValueError(reason="second"))

    assert str(sink.errors[segment]) == "VALIDATION.INVALID_VALUE(reason=first)"
