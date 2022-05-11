from pymongo.errors import DuplicateKeyError


class Mongo:
    @staticmethod
    def extract_unique_violation(exception: DuplicateKeyError) -> str:
        return exception.details["errmsg"].split(":", 2)[2].split(" ", 2)[1]
