import sys
from os.path import isfile, join as join_path
from itertools import accumulate, chain
from importlib import import_module


def find_file(filename: str, path: list) -> str:
    for p in path:
        f = join_path(p, filename)
        if isfile(f):
            return f
    return None


def file_path_from_module_name(*parts):
    _split = lambda s: s.split('.') if isinstance(s, str) else s
    components = chain.from_iterable(_split(part) for part in parts if part)
    return join_path(*components) + '.py'


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


if sys.version_info > (3, 5):
    from importlib.util import spec_from_file_location, module_from_spec
    def _load_source(name, path, context=None):
        spec = spec_from_file_location(name, path)
        module = module_from_spec(spec)
        if context:
            for key, value in context.items():
                setattr(module, key, value)
        spec.loader.exec_module(module)
        return module
else:
    raise ImportError("Library requires python version 3.5+. Currently running python %s" % (sys.version,))

def load_module_from_file(name, path, context=None):
    assert path.endswith('.py'), "Trying to load python from a file that doesn't end in .py: %s" % (path,)

    if not isfile(path):
        return None

    return _load_source('__load_module_from_fule_' + name, path, context=context)
