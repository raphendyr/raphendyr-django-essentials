import sys
from importlib import import_module


def find_and_import_module(base, name):
    """
    Try to find and import module starting from peer of the base
    and continueing to root:

    For base='foo.bar.baz' and name='something' try:
    foo.bar.something, foo.something, something
    """
    tried = []
    module = None
    while base:
        base = base.rpartition('.')[0]
        test = (base+'.' if base else '') + name
        tried.append(test)
        try:
            module = import_module(test)
            break
        except ImportError:
            pass
    return module, tried


def unload_module(module):
    """
    Removes module from loaded modules dictionary.
    If there is no more references to the module, python should remove it from memory.
    """
    name = module if isinstance(module, str) else module.__name__
    try:
        del sys.modules[name]
    except KeyError:
        pass
