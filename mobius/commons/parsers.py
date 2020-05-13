import hashlib
from calendar import timegm
from datetime import (
    datetime,
    timedelta,
)
from decimal import (
    Decimal,
    DecimalException,
)
from functools import singledispatch
from pathlib import Path
from random import randint
from typing import (
    Any,
    Optional,
    Union,
)
from uuid import (
    UUID,
    uuid4,
)

from bson import ObjectId


def parse_uuid(str_uuid: str, default=None) -> Optional[UUID]:
    try:
        if isinstance(str_uuid, bytes):
            str_uuid = str_uuid.decode()
        if not isinstance(str_uuid, UUID):
            return UUID(str_uuid)
        else:
            return str_uuid
    except (ValueError, TypeError, AttributeError):
        return default


def parse_object_id(object_id: str, default=None) -> Optional[ObjectId]:
    try:
        return ObjectId(object_id.decode() if isinstance(object_id, bytes) else object_id)
    except (ValueError, TypeError, AttributeError):
        return default


@singledispatch
def parse_bool(value: Any, default=None) -> Optional[bool]:
    return default


@parse_bool.register(int)
def parse_bool_int(value: int, default=None) -> Optional[bool]:
    if value == 1:
        return True
    elif value in {-1, 0}:
        return False
    else:
        return default


@parse_bool.register(str)
def parse_bool_str(value: str, default=None) -> Optional[bool]:
    value = value.lower().strip()
    if value in {"1", "true"}:
        return True
    elif value in {"0", "false"}:
        return False
    else:
        return default


@parse_bool.register(bool)
def parse_bool_bool(value: bool, default=None) -> Optional[bool]:
    return value


def parse_int(value: Union[float, int, str], default: Optional[int] = 0):
    try:
        out = int(value)
    except (ValueError, TypeError):
        out = default
    return out


def parse_decimal(value: Union[float, int, str], default: Optional[Decimal] = None):
    try:
        out = Decimal(value)
        return out

    except DecimalException:
        return default


def parse_float(value: Union[float, int, str], default: Optional[Union[float, int]] = 0):
    try:
        out = float(value)
    except (ValueError, TypeError):
        out = default
    return out


def get_unixtimestamp(date: datetime = None) -> int:
    """
    Converts date and time to unix timestamp
    If date is not provided then it takes current time and convert it to unix timestamp
    :param date: datetime
    :return: int
    """
    if not date or not isinstance(date, datetime):
        date = datetime.utcnow()
    return timegm(date.utctimetuple())


def from_str_to_unixtimestamp(date_str: str, str_format='%Y-%m-%d') -> Optional[int]:
    try:
        date = datetime.strptime(date_str, str_format)
        return get_unixtimestamp(date)
    except (ValueError, TypeError):
        return None


def last_day_of_month(any_day):
    next_month = any_day.replace(day=28) + timedelta(days=4)  # this will never fail
    return next_month - timedelta(days=next_month.day)


def unixtimestamp_to_str(timestamp, str_format='%Y-%m-%d'):
    return datetime.utcfromtimestamp(timestamp).strftime(str_format)


def uts_to_str(timestamp=None, str_format='%Y-%m-%dT%H:%M:%SZ'):
    return unixtimestamp_to_str(timestamp, str_format) if timestamp else ''


def date_to_iso(data: datetime) -> str:
    return data.strftime('%Y-%m-%dT%H:%M:%SZ')


def generate_token():
    return "".join([str(randint(100, 999)), str(uuid4()).replace('-', '')])


def file_md5(file_path):
    chunk_size = 8129
    with Path(file_path).open('rb') as file_handler:
        file_hash = hashlib.md5()
        file_chunk = file_handler.read(chunk_size)
        while file_chunk:
            file_hash.update(file_chunk)
            file_chunk = file_handler.read(chunk_size)
        return file_hash.hexdigest()
