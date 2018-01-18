import sys
from itertools import accumulate, chain
from importlib import import_module


def find_and_import_module(name, search=None):
    """
    Search module by name under every component of base.
    Given name='foo' and base='bar' we will test modules 'bar.foo' and 'foo'.
    """
    # generate tuples: (), ('foo'), ('foo', 'bar'), ...
    search = chain(((),), accumulate((x,) for x in search.split('.'))) if search else ((),)
    # create python modules: 'm', 'foo.m', 'foo.bar.m', ...
    name_t = (name,)
    modules = ['.'.join(x + name_t) for x in search]
    # start from the right
    modules.reverse()

    for module in modules:
        try:
            return import_module(module), ()
        except ImportError:
            pass
    return None, modules


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
