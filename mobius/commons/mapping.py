"""Error-accumulating JSON-to-model mapping, ported from kload's Kotlin mapper.

One ErrorSink is shared by every context of a mapping run; contexts report
errors with their full segment, so a broken document yields *all* problems at
once ("sources.db.connectionUrl: INVALID_TYPE(Str)") instead of dying on the
first missing key. The target is only built inside construct(), which runs
solely when the run is error-free — that is what makes Checked.require() safe.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Generic, Tuple, TypeVar


T = TypeVar("T")
R = TypeVar("R")

DEFAULT_MAX_ERRORS = 10


class Segment:
    __slots__ = ("parts",)

    def __init__(self, parts: Tuple[str, ...] = ()):
        self.parts = parts

    def push(self, part: str) -> "Segment":
        return Segment(self.parts + (part,))

    def __str__(self):
        return "$" + "".join(f".{part}" for part in self.parts)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return isinstance(other, Segment) and self.parts == other.parts

    def __hash__(self):
        return hash(self.parts)


EMPTY_SEGMENT = Segment()


class FieldError:
    __slots__ = ("code", "params")

    def __init__(self, code: str, **params):
        self.code = code
        self.params = params

    def __str__(self):
        if self.params:
            details = ", ".join(
                f"{key}={value}" for key, value in sorted(self.params.items())
            )
            return f"{self.code}({details})"
        return self.code

    def __repr__(self):
        return self.__str__()


class NullValueError(FieldError):
    def __init__(self):
        super().__init__("VALIDATION.NULL_VALUE")


class RequiredKeyMissingError(FieldError):
    def __init__(self):
        super().__init__("VALIDATION.REQUIRED_KEY_MISSING")


class InvalidTypeError(FieldError):
    def __init__(self, type: str):
        super().__init__("VALIDATION.INVALID_TYPE", type=type)


class InvalidValueError(FieldError):
    def __init__(self, **params):
        super().__init__("VALIDATION.INVALID_VALUE", **params)


class MappingException(Exception):
    def __init__(self, errors: Dict[Segment, FieldError]):
        self.errors = errors

        details = "; ".join(f"{segment}: {error}" for segment, error in errors.items())
        super().__init__(f"Mapping failed with {len(errors)} error(s): {details}")


class MaxMappingErrorsExceededException(Exception):
    """Control-flow signal raised by ErrorSink once the error cap is reached.

    Translated by map_object into MappingException; never exposed to callers.
    """


class ErrorSink:
    __slots__ = ("max_errors", "_errors")

    def __init__(self, max_errors: int = DEFAULT_MAX_ERRORS):
        self.max_errors = max_errors
        self._errors: Dict[Segment, FieldError] = {}

    @property
    def errors(self) -> Dict[Segment, FieldError]:
        return self._errors

    @property
    def has_errors(self) -> bool:
        return bool(self._errors)

    def report(self, segment: Segment, error: FieldError):
        if len(self._errors) >= self.max_errors:
            raise MaxMappingErrorsExceededException()

        self._errors.setdefault(segment, error)


class Checked(Generic[T]):
    """Result of a single field extraction: the value (or None after a reported
    error) together with the field's full segment, so follow-up validation via
    must() reports to the right location."""

    __slots__ = ("_raw", "segment", "_sink")

    def __init__(self, raw: T | None, segment: Segment, sink: ErrorSink):
        self._raw = raw
        self.segment = segment
        self._sink = sink

    def or_none(self) -> T | None:
        return self._raw

    def or_else(self, default: T) -> T:
        return self._raw if self._raw is not None else default

    def require(self) -> T:
        """Only safe inside construct(), which runs solely when no errors were
        reported."""
        if self._raw is None:
            raise AssertionError(
                f"Value at '{self.segment}' is absent or invalid; "
                f"require() is only safe inside construct()"
            )

        return self._raw

    def must(
        self, error: FieldError, predicate: Callable[[T], bool]
    ) -> "Checked[T]":
        if self._raw is None:
            return self

        if not predicate(self._raw):
            self._sink.report(self.segment, error)
            return Checked(None, self.segment, self._sink)

        return self

    def map(self, transform: Callable[[T], R]) -> "Checked[R]":
        raw = None if self._raw is None else transform(self._raw)
        return Checked(raw, self.segment, self._sink)

    def try_map(
        self,
        error: Callable[[T], FieldError],
        transform: Callable[[T], R],
    ) -> "Checked[R]":
        """map() for transforms that signal bad input by throwing: a throw
        reports the error at this field's segment and empties the value."""
        if self._raw is None:
            return Checked(None, self.segment, self._sink)

        try:
            return Checked(transform(self._raw), self.segment, self._sink)
        except Exception:
            self._sink.report(self.segment, error(self._raw))
            return Checked(None, self.segment, self._sink)


def _as_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _as_object(value: Any) -> dict | None:
    return value if isinstance(value, dict) else None


def _as_string_map(value: Any) -> Dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    if not all(isinstance(item, str) for item in value.values()):
        return None
    return value


class ObjectContext:
    __slots__ = ("node", "sink", "segment")

    def __init__(self, node: dict, sink: ErrorSink, segment: Segment = EMPTY_SEGMENT):
        self.node = node
        self.sink = sink
        self.segment = segment

    def report(self, error: FieldError, field: str | None = None):
        segment = self.segment.push(field) if field else self.segment
        self.sink.report(segment, error)

    def construct(self, factory: Callable[[], T]) -> T | None:
        """Gate for building the target value: runs factory only when the whole
        run is error-free, which is what makes Checked.require() safe inside
        it. When any error was reported the result is discarded by map_object
        anyway, so this simply returns None."""
        return None if self.sink.has_errors else factory()

    # required field: missing key and null are errors
    def get_string(self, field: str) -> Checked[str]:
        return self._get_field(field, "Str", _as_string)

    def get_int(self, field: str) -> Checked[int]:
        return self._get_field(field, "Int", _as_int)

    def get_float(self, field: str) -> Checked[float]:
        return self._get_field(field, "Float", _as_float)

    def get_bool(self, field: str) -> Checked[bool]:
        return self._get_field(field, "Bool", _as_bool)

    # optional field: missing key and null yield an empty Checked, no error
    def find_string(self, field: str) -> Checked[str]:
        return self._find_field(field, "Str", _as_string)

    def find_int(self, field: str) -> Checked[int]:
        return self._find_field(field, "Int", _as_int)

    def find_float(self, field: str) -> Checked[float]:
        return self._find_field(field, "Float", _as_float)

    def find_bool(self, field: str) -> Checked[bool]:
        return self._find_field(field, "Bool", _as_bool)

    def find_string_map(self, field: str) -> Checked[Dict[str, str]]:
        return self._find_field(field, "StringMap", _as_string_map)

    def find_raw_object(self, field: str) -> Checked[dict]:
        return self._find_field(field, "Object", _as_object)

    def get_object(
        self, field: str, block: Callable[["ObjectContext"], T | None]
    ) -> Checked[T]:
        return self._nested(self._get_field(field, "Object", _as_object), block)

    def find_object(
        self, field: str, block: Callable[["ObjectContext"], T | None]
    ) -> Checked[T]:
        return self._nested(self._find_field(field, "Object", _as_object), block)

    def _get_field(
        self, field: str, type_name: str, convert: Callable[[Any], T | None]
    ) -> Checked[T]:
        field_segment = self.segment.push(field)

        if field not in self.node:
            self.sink.report(field_segment, RequiredKeyMissingError())
            return Checked(None, field_segment, self.sink)

        value = self.node[field]
        if value is None:
            self.sink.report(field_segment, NullValueError())
            return Checked(None, field_segment, self.sink)

        return self._converted(field_segment, value, type_name, convert)

    def _find_field(
        self, field: str, type_name: str, convert: Callable[[Any], T | None]
    ) -> Checked[T]:
        field_segment = self.segment.push(field)

        value = self.node.get(field)
        if value is None:
            return Checked(None, field_segment, self.sink)

        return self._converted(field_segment, value, type_name, convert)

    def _converted(
        self,
        field_segment: Segment,
        value: Any,
        type_name: str,
        convert: Callable[[Any], T | None],
    ) -> Checked[T]:
        converted = convert(value)
        if converted is None:
            self.sink.report(field_segment, InvalidTypeError(type=type_name))

        return Checked(converted, field_segment, self.sink)

    def _nested(
        self,
        source: Checked[dict],
        block: Callable[["ObjectContext"], T | None],
    ) -> Checked[T]:
        inner = source.or_none()
        if inner is None:
            return Checked(None, source.segment, self.sink)

        value = block(ObjectContext(inner, self.sink, source.segment))
        return Checked(value, source.segment, self.sink)


def map_object(
    data: Any,
    block: Callable[[ObjectContext], T | None],
    max_errors: int = DEFAULT_MAX_ERRORS,
) -> T:
    """Run one mapping over data, raising MappingException carrying every
    reported error (keyed by segment) when anything went wrong."""
    sink = ErrorSink(max_errors)

    if not isinstance(data, dict):
        sink.report(EMPTY_SEGMENT, InvalidTypeError(type="Object"))
        raise MappingException(sink.errors)

    try:
        value = block(ObjectContext(data, sink))
    except MaxMappingErrorsExceededException:
        value = None

    if sink.has_errors:
        raise MappingException(sink.errors)

    return value
