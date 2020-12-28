import json
from io import TextIOWrapper
from typing import Dict

from mobius.drivers.manager import (
    DriverJsonMapper,
    IDriverConfig,
)


class MobiusConfig:
    __slots__ = ('state', 'sources')
    state: IDriverConfig
    sources: Dict[str, IDriverConfig]

    def __init__(self,
                 state: IDriverConfig,
                 sources: Dict[str, IDriverConfig]):
        self.state = state
        self.sources = sources


class MobiusJsonMapper:
    __slots__ = ()

    class Fields:
        __slots__ = ()
        STATE = "state"
        SOURCES = "sources"

    @classmethod
    def from_json(cls, raw_json: dict, driver_mapper: DriverJsonMapper) -> MobiusConfig:
        _ = cls.Fields

        state = raw_json[_.STATE]
        sources = raw_json[_.SOURCES]

        state_driver = driver_mapper.from_json('state', state)

        sources = {name: driver_mapper.from_json(name, driver_config) for name, driver_config in sources.items()}

        return MobiusConfig(state_driver, sources)


class MobiusFileMapper:
    __slots__ = ('driver_mapper',)

    def __init__(self, driver_mapper: DriverJsonMapper):
        self.driver_mapper = driver_mapper

    def from_file(self, file: TextIOWrapper) -> MobiusConfig:
        with file:
            contents = json.load(file)

        return MobiusJsonMapper.from_json(contents, self.driver_mapper)
