from datetime import datetime
from decimal import Decimal
from typing import (
    Any,
    Callable,
    List,
    Optional,
)
from uuid import UUID

from mobius.commons.validation.errors import (
    error_missing,
    invalid_array,
    invalid_bool,
    invalid_data,
    invalid_datetime,
    invalid_fixed_float,
    invalid_number,
    invalid_string,
    invalid_uuid,
    too_big,
    too_small,
)
from mobius.commons.validation.parsers import (
    parse_bool,
    parse_decimal,
    parse_int,
    parse_uuid,
)


class Str:
    __slots__ = ()

    @staticmethod
    def map(data: dict, field_name: str, errors: dict, required: bool = True, minimal: int = None, error_field: str = None) -> Optional[str]:
        field_value = data.get(field_name)
        error_field = error_field if error_field else field_value

        return Str.cast(field_value, error_field, errors, required, minimal)

    @staticmethod
    def parse(value: Any, encoding: Optional[str] = "UTF-8") -> Optional[str]:
        if isinstance(value, str):
            return value
        if isinstance(value, bytes) and encoding:
            return value.decode(encoding)

    @staticmethod
    def cast(value: Any, error_field: str, errors: dict, required: bool = True, minimal: Optional[int] = None, default: Optional[str] = None) -> Optional[str]:
        field_value = default
        if not value:
            if required:
                errors[error_field] = error_missing
        else:
            field_value = Str.parse(value)

            if field_value is None or not isinstance(field_value, str):
                errors[error_field] = invalid_string
            elif minimal and len(field_value) < minimal:
                errors[error_field] = too_small(minimal)

        return field_value


class Uuid:
    @staticmethod
    def map(data: dict, field_name: str, errors: dict, required: bool = True, error_field: str = None) -> Optional[UUID]:
        field_value = data.get(field_name)

        error_field = error_field if error_field else field_name

        if not field_value:
            if required:
                errors[error_field] = error_missing
        else:
            field_value = parse_uuid(field_value)

            if field_value is None:
                errors[error_field] = invalid_uuid

        return field_value


def to_uuid(value: Any, error_field: str, errors: dict, required: bool = True, default=None):
    field_value = default
    if not value:
        if required:
            errors[error_field] = error_missing
    else:
        field_value = parse_uuid(value)

        if field_value is None:
            errors[error_field] = invalid_uuid

    return field_value


def map_uuid(data: dict, field_name: str, errors: dict, required: bool = True, error_field: str = None) -> Optional[UUID]:
    field_value = data.get(field_name)

    error_field = error_field if error_field else field_name

    if not field_value:
        if required:
            errors[error_field] = error_missing
    else:
        field_value = parse_uuid(field_value)

        if field_value is None:
            errors[error_field] = invalid_uuid

    return field_value


def map_int(data: dict, field_name: str, errors: dict, default: Optional[int] = None, required: bool = True, min: int = None, max: int = None) -> Optional[int]:
    field_value = data.get(field_name)

    if field_value is None:
        if required:
            errors[field_name] = error_missing
        else:
            field_value = default
    else:
        field_value = parse_int(field_value, default=None)

        if field_value is None:
            errors[field_name] = invalid_number
        else:
            if min and field_value < min:
                errors[field_name] = too_small(min)
            elif max and field_value > max:
                errors[field_name] = too_big(max)

    return field_value


def map_decimal(data: dict, field_name: str, errors: dict, required: bool = True, min: Decimal = None, max: Decimal = None) -> Optional[Decimal]:
    field_value = data.get(field_name)

    if field_value is None:
        if required:
            errors[field_name] = error_missing
    else:
        field_value = parse_decimal(field_value, default=None)

        if field_value is None:
            errors[field_name] = invalid_fixed_float
        else:
            if min and field_value < min:
                errors[field_name] = too_small(min)
            elif max and field_value > max:
                errors[field_name] = too_big(max)

    return field_value


def map_iso_datetime(data: dict, field_name: str, errors: dict, required: bool = True, min: datetime = None, max: datetime = None) -> Optional[datetime]:
    field_value = data.get(field_name)

    if not field_value:
        if required:
            errors[field_name] = error_missing
    else:
        field_value = parse_date(field_value)  # TODO

        if field_value is None:
            errors[field_name] = invalid_datetime
        elif min and min > field_value:
            errors[field_name] = too_small(min)
        elif max and max < field_value:
            errors[field_name] = too_big(max)

    return field_value


def map_date(data: dict, field_name: str, errors: dict, required: bool = True, format: str = "%d-%m-%Y", min: datetime = None, max: datetime = None) -> Optional[datetime]:
    field_value = data.get(field_name)

    if not field_value:
        if required:
            errors[field_name] = error_missing
    else:
        try:
            field_value = datetime.strptime(field_value, format)

            if min and min > field_value:
                errors[field_name] = too_small(min)
            elif max and max < field_value:
                errors[field_name] = too_big(max)
        except (ValueError, TypeError):
            errors[field_name] = invalid_data

    return field_value


def map_boolean(data: dict, field_name: str, errors: dict, required: bool = True, default: bool = None, error_field: str = None) -> Optional[bool]:
    field_value = data.get(field_name)

    error_field = error_field if error_field else field_name

    if field_value is None:
        if required:
            errors[error_field] = error_missing
    else:
        field_value = parse_bool(field_value)

        if field_value is None:
            errors[error_field] = invalid_bool

    if field_value is None:
        field_value = default

    return field_value


def map_list(data: dict, field_name: str, mapper: Callable, errors: dict, required: bool = True, default=None, error_field: str = None) -> Optional[List]:
    field_value = data.get(field_name)

    error_field = error_field if error_field else field_name
    mapped_values = []

    if field_value is None:
        if required:
            errors[error_field] = error_missing
    else:
        if not isinstance(field_value, list):
            errors[error_field] = invalid_array
        else:
            for index, row in enumerate(field_value):
                value = mapper(row, f'{error_field}.[{index}]', errors, required, default)
                if value is None:
                    value = default
                mapped_values.append(value)

    return mapped_values


def map_list_uuid(data: dict, field_name: str, errors: dict, required: bool = True, default=None, error_field: str = None) -> Optional[List[UUID]]:
    return map_list(data, field_name, to_uuid, errors, required, default, error_field)
