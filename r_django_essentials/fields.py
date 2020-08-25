import enum
from collections import OrderedDict


class Enum(object):
    """
    Represents constant enumeration.

    Usage:
        OPTS = Enum(
            ('FOO', 1, 'help string for foo'),
            ('BAR', 2, 'help string for bar'),
        )

        if OPTS.FOO == test_var:
            return OPTS[test_var]

        ChoicesField(choices=OPTS.choices)
    """
    def __init__(self, *choices):
        if len(choices) == 1 and isinstance(choices[0], (tuple, list)):
            choices = choices[0]
        self._strings = OrderedDict()
        self._keys = []
        for name, value, string in choices:
            assert value not in self._strings, "Multiple choices have same value"
            self._strings[value] = string
            self._keys.append(name)
            setattr(self, name, value)

    @property
    def choices(self):
        return tuple(self._strings.items())

    def keys(self):
        return (x for x in self._keys)

    def __getitem__(self, key):
        return self._strings[key]

    def __str__(self):
        s = ["<%s([" % (self.__class__.__name__,)]
        for key in self.keys():
            val = getattr(self, key)
            txt = self[val]
            s.append("  (%s, %s, %s)," % (key, val, txt))
        s.append("])>")
        return '\n'.join(s)

class EnumChoices(enum.Enum):
    def __init__(self, value, description):
        self._value_ = value
        self.description = description

    @classmethod
    def choices(cls):
        return tuple((item.value, item.description) for item in cls.__members__.values())
