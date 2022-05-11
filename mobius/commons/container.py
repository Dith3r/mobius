class Container:
    pass


# noinspection PyPep8Naming
class cached_property:
    __slots__ = ("_constructor", "_name")

    def __init__(self, constructor):
        self._constructor = constructor
        self._name = f"_{constructor.__name__}"

    def __get__(self, container, instance):
        property = container.__dict__.get(self._name)
        if property is None:
            property = self._constructor(container)
            container.__dict__[self._name] = property
        return property
