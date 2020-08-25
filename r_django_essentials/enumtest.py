from fields import EnumChoices

class A(EnumChoices):
    FOO = 2, "foo"
    BAR = 3, "bar"

_ = lambda x: print(repr(x))
_(A.FOO)
_(A.BAR)
_(A.FOO.value)
_(A.choices())
_(A(2))
