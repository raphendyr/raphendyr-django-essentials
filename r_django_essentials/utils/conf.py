import sys
from os.path import abspath, dirname
from django.apps import AppConfig

from .django import get_random_secret_key


def ensure_app_configs(apps):
    """
    Generator that will make sure all values in iterator are AppConfigs
    """
    c = AppConfig.create
    for entry in apps:
        yield entry if isinstance(entry, AppConfig) else c(entry)


def create_secret_key_file(filename, setting=None):
    """
    Generate new key and store it in the file.
    """
    key = get_random_secret_key()
    setting = setting or 'SECRET_KEY'
    with open(filename, 'w') as file:
        file.write('''"""
Automatically generated file.
This needs to be unique and SECRET. It is also installation specific.
This file should be included from settings.py
"""
{} = '{}'
'''.format(setting, key))
    return key


def flatten_loaders(loaders):
    """
    Flatten loaders structure
    """
    all_loaders = set()
    if loaders:
        for loader in loaders:
            if isinstance(loader, str):
                all_loaders.add(loader)
            elif isinstance(loader, (list, tuple)):
                all_loaders |= flatten_loaders(loader)
    return all_loaders


class SettingsDict:
    """
    Class that wraps module so it can be manipualted with dict operations.
    """
    @classmethod
    def ensure(cls, obj):
        if isinstance(obj, cls):
            return obj
        elif isinstance(obj, str):
            return cls(obj)
        else:
            raise ValueError("Invalid object for SettingsDict.ensure()")

    def __init__(self, name):
        self.name = name
        self.module = sys.modules[name]

    @property
    def file(self):
        return self.module.__file__

    @property
    def path(self):
        return abspath(dirname(self.module.__file__))

    def __setitem__(self, key, value):
        setattr(self.module, key, value)

    def __contains__(self, key):
        return hasattr(self.module, key)

    def __getitem__(self, key):
        try:
            return getattr(self.module, key)
        except AttributeError as e:
            raise KeyError(e)

    def keys(self):
        return dir(self.module)

    def items(self):
        return ((k, self[k]) for k in self.keys())

    def values(self):
        return (v for k, v in self.items())

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def update(self, data):
        m = self.module
        for key, value in data.items():
            setattr(m, key, value)
