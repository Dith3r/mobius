import hashlib
import re
from pathlib import Path
from typing import List, TypeVar


URL_PASSWORD = re.compile(r"//([^/:@]+):([^/@]*)@")


def mask_url_credentials(url: str) -> str:
    """Mask the password part of a URL's userinfo for safe logging."""
    return URL_PASSWORD.sub(r"//\1:***@", url)


T = TypeVar("T")


def chunk(data: List[T], size: int):
    for i in range(0, len(data), size):
        yield data[i : i + size]  # noqa


def reverse_map(data: dict) -> dict:
    return {value: key for key, value in data.items()}


def file_md5(file_path):
    chunk_size = 8129
    with Path(file_path).open("rb") as file_handler:
        file_hash = hashlib.md5()
        file_chunk = file_handler.read(chunk_size)
        while file_chunk:
            file_hash.update(file_chunk)
            file_chunk = file_handler.read(chunk_size)
        return file_hash.hexdigest()
