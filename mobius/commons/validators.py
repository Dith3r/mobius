from dataclasses import dataclass
from typing import (
    Optional,
    TypeVar,
)

T = TypeVar('T')


@dataclass
class Error:
    __slots__ = ('code', 'parameters')
    code: str
    parameters: Optional[dict]

    @classmethod
    def new(cls, code: str):
        return cls(code, None)

    def to_dict(self):
        return {"code": self.code} if not self.parameters else {"code": self.code, "parameters": self.parameters}


class ValidationException(Exception):
    __slots__ = ('parameters', 'code')

    def __init__(self, parameters: Optional[dict] = None, code: str = None):
        self.parameters = parameters
        self.code = f"VALIDATION.{code}" if code else "VALIDATION.ERROR"

    @classmethod
    def single(cls, field, error):
        return cls(parameters={field: error})

    @classmethod
    def general(cls, error: Error):
        return cls(code=error.code, parameters=error.parameters)

    def extract(self, prefix: str = "", errors=None):
        if errors is None:
            errors = {}

        if prefix:
            prefix = f"{prefix}."

        for field, error in self.parameters.items():
            errors[f"{prefix}{field}"] = error

        return errors

    def extract_indexed(self, index: int, errors=None):
        return self.extract(f'[{index}]', errors)
