class Json:
    __slots__ = ()
    SEPARATOR = "."

    @classmethod
    def join_key(cls, *fields: str) -> str:
        return cls.SEPARATOR.join(fields)
