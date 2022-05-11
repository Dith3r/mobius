class UniqueViolationError(Exception):
    def __init__(self, index: str) -> None:
        self.index = index
