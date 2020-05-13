from mobius.commons.validators import Error

invalid_object = Error("INVALID_KIND", {"expected": "object"})
invalid_array = Error("INVALID_KIND", {"expected": "array"})
invalid_string = Error("INVALID_KIND", {"expected": "string"})
invalid_uuid = Error("INVALID_KIND", {"expected": "UUID"})
invalid_data = Error("INVALID_KIND", {"expected": "date"})
invalid_datetime = Error("INVALID_KIND", {"expected": "datetime"})
invalid_bool = Error("INVALID_KIND", {"expected": "bool"})
invalid_number = Error("INVALID_KIND", {"expected": "number"})
invalid_fixed_float = Error("INVALID_KIND", {"expected": "fixedFloat"})

error_missing = Error.new("MISSING")


def too_small(min):
    return Error("TOO_SMALL", {"required": min})


def too_big(max):
    return Error("TOO_BIG", {"required": max})
