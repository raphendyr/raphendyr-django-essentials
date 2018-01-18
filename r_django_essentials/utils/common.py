import sys
from warnings import warn


__all__ = [
    'warning',
    'unique',
]


def warning(message):
    """
    Show error using warnings module. Shows function from stack that called this function.
    """
    warn(message, stacklevel=3)


if sys.version_info > (3, 5):
    from collections import OrderedDict

    def unique(seq):
        """
        Remove duplicates from sequence. Uses OrderedDict.
        """
        # in python 3.5+ OrderedDict has C implementation -> fastest
        return OrderedDict.fromkeys(seq).keys()

else:
    def unique(seq):
        """
        Remove duplicates from sequence. Uses generator and set.
        """
        seen = set()
        see = seen.add
        return (x for x in seq if not (x in seen or see(x)))

