import functools
from warnings import warn
from django.utils.deprecation import RemovedInNextVersionWarning


def deprecated(message, category=None):
    '''
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    '''
    category = category or RemovedInNextVersionWarning
    def wrapper(func):
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            warn(message, category=category, stacklevel=2)
            return func(*args, **kwargs)
        return new_func
    return wrapper
