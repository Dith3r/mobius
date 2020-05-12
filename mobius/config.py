import json

from io import TextIOWrapper


class MobiusConfig:
    ...

    @classmethod
    def from_file(cls, file):
        return MobiusFileMapper.from_file(file)


class MobiusJsonMapper:
    __slots__ = ()

    class Fields:
        __slots__ = ()
        STATE = "state"

    @classmethod
    def from_json(cls, json: dict) -> MobiusConfig:
        ...


class MobiusFileMapper:
    __slots__ = ()

    @classmethod
    def from_file(cls, file: TextIOWrapper) -> MobiusConfig:
        with file:
            contents = json.load(file)

            return MobiusJsonMapper.from_json(contents)
