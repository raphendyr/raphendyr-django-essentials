from os import environ
from os.path import join as join_path
from sys import stderr
from collections import Iterable, OrderedDict, defaultdict
from itertools import chain
from json import loads as json_loads, JSONDecodeError

from .helpers import (
    ensure_app_configs,
    find_and_import_module,
    unload_module,
    create_secret_key_file,
    flatten_loaders,
    SettingsDict,
)
from .utils import (
    unique,
    warning,
)


__all__ = [
    'update_settings',
    'update_settings_from_module',
    'update_secret_from_file',
    'update_settings_from_environment',
    'update_installed_apps',
    'update_context_processors_from_apps',
    'use_cache_template_loader_in_production',
]


DEFAULT_REQUIRED_APPS_OPTION = 'required_apps'
DEFAULT_CONTEXT_PROCESSORS_OPTION = 'context_processors'
DEFAULT_TEMPLATE_BACKEND = 'django.template.backends.django.DjangoTemplates'
DEFAULT_ENVIRONMENT_PREFIX = 'DJANGO_'
DEFAULT_CACHED_LOADER = 'django.template.loaders.cached.Loader'
DEFAULT_LOADER = 'django.template.loaders.filesystem.Loader'
DEFAULT_APP_LOADER = 'django.template.loaders.app_directories.Loader'
DEFAULT_LOCAL_SETTINGS_FILE = 'local_settings'
DEFAULT_SECRET_KEY_FILE = 'secret_key'


def expand_required_apps(installed_apps, option=None):
    """
    Given list of django applications will be expanded
    with required applications from AppConfig of the app
    """
    option = option or DEFAULT_REQUIRED_APPS_OPTION
    visited = set()
    expanded = []

    def populate(apps):
        for appc in ensure_app_configs(apps):
            name = appc.name
            if name not in visited:
                visited.add(name)

                required_apps = getattr(appc, option, None)
                if required_apps:
                    populate(required_apps)

                expanded.append(appc)

    populate(installed_apps)
    return tuple(expanded)


def add_required_context_processors(templates, installed_apps, option=None):
    """
    Will resolve context processors from AppConfigs and add them to
    templates (list of backend configurations).
    """
    option = option or DEFAULT_CONTEXT_PROCESSORS_OPTION
    processors = defaultdict(list)

    for appc in ensure_app_configs(installed_apps):
        required_cps = getattr(appc, option, None)
        if not required_cps:
            continue

        if isinstance(required_cps, str):
            required_cps = { DEFAULT_TEMPLATE_BACKEND: (required_cps,) }
        elif isinstance(required_cps, Iterable): # note: str is Iterable
            required_cps = { DEFAULT_TEMPLATE_BACKEND: required_cps }

        for backend, cps in required_cps.items():
            processors[backend].extend(cps)

    templates_map = OrderedDict((x.get('BACKEND'), x) for x in templates)

    for backend, cps in processors.items():
        conf = templates_map.get(backend)
        if conf:
            options = conf.setdefault('OPTIONS', {})
            all_cps = chain(options.get('context_processors', ()), cps)
            options['context_processors'] = tuple(unique(all_cps))


# Simple update functions that work on settigns dict

def update_settings_from_environment(settings, env_prefix=None, quiet=False):
    """
    Load overrides to settings from environment.
    All environment variables starting with DJANGO_ will be parsed as
    JSON strings (fallback to string) and updated to settings dict.
    """
    settings = SettingsDict.ensure(settings)
    if env_prefix is None:
        env_prefix = DEFAULT_ENVIRONMENT_PREFIX
    prefix_len = len(env_prefix)
    keys = [key for key in environ if key.startswith(env_prefix)]
    if 'DJANGO_SETTINGS_MODULE' in keys:
        keys.remove('DJANGO_SETTINGS_MODULE')

    for key in keys:
        setting_value = environ[key]
        try:
            setting_value = json_loads(setting_value)
        except JSONDecodeError:
            pass

        setting = key[prefix_len:]
        settings[setting] = setting_value
        if not quiet:
            print("Note: defined settings.{} from environment".format(setting), file=stderr)


def update_settings_from_module(settings, module_name, search_base=None, quiet=False):
    """
    Update settings module with uppwer case values from another module.
    Use for example to include values from local_settings.py

    `update_settings_from_module(__name__, 'local_settings')` for example.
    """
    settings = SettingsDict.ensure(settings)
    module, tried = find_and_import_module(search_base or settings.name, module_name)
    name = module.__name__

    if module:
        data = {setting: getattr(module, setting) for setting in dir(module) if setting.isupper()}
        settings.update(data)
        unload_module(module) # module can be removed from memory as all the data in it has been loaded
        del module
        return len(data)
    else:
        if not quiet:
            warning("Couldn't find {}.py. Tried: {}".format(module_name, tried))
        return 0


def update_secret_from_file(settings, secret_key_file=None, base=None, setting=None):
    """
    Will update only single value from module. If the module doesn't exists, will create the file with new secret key
    """
    settings = SettingsDict.ensure(settings)
    secret_key_file = secret_key_file or DEFAULT_SECRET_KEY_FILE
    setting = setting or 'SECRET_KEY'

    if settings.get(setting):
        # We already have non null secret_key
        return

    module, tried = find_and_import_module(base or settings.name, secret_key_file)

    if module:
        if hasattr(module, setting):
            settings[setting] = getattr(module, setting)
        else:
            warning("File {} doesn't contain {}. To create new key, remove the file.".format(module.__file__, setting))
        unload_module(module) # module can be moved from memory as all the data in it has been loaded
        del module
    else:
        settings_dir = settings.path
        key_filename = join_path(settings_dir, secret_key_file+'.py')
        try:
            key = create_secret_key_file(key_filename, setting=setting)
        except IOError as e:
            warning("Secret key is not defined and we were unable to create {}: {}".format(key_filename, e))
        else:
            warning("Created new {} in {}".format(setting, key_filename))
            settings[setting] = key


def update_installed_apps(settings, apps_option=None):
    """
    Update INSTALLED_APPS setting by expanding requirements from AppConfigs
    """
    settings = SettingsDict.ensure(settings)
    installed_apps = settings.get('INSTALLED_APPS')
    if installed_apps:
        installed_apps = expand_required_apps(installed_apps, option=apps_option)
        settings['INSTALLED_APPS'] = installed_apps


def update_context_processors_from_apps(settings, processors_option=None):
    """
    Update TEMPLATES setting by adding context_processors from AppConfigs
    """
    settings = SettingsDict.ensure(settings)
    installed_apps = settings.get('INSTALLED_APPS')
    templates = settings.get('TEMPLATES')
    if installed_apps and templates:
        add_required_context_processors(templates, installed_apps, option=processors_option)


def use_cache_template_loader_in_production(settings):
    """
    Wrap template loaders with cached loader on production (DEBUG = False)
    """
    settings = SettingsDict.ensure(settings)
    debug = settings.get('DEBUG', False)
    templates = settings.get('TEMPLATES')

    if not debug and templates:
        for conf in templates:
            options = conf.setdefault('OPTIONS', {})
            loaders = options.get('loaders')
            if not loaders or DEFAULT_CACHED_LOADER not in flatten_loaders(loaders):
                if not loaders:
                    loaders = (DEFAULT_LOADER,)
                    if conf.get('APP_DIRS', False):
                        loaders += (DEFAULT_APP_LOADER,)
                loaders = ((DEFAULT_CACHED_LOADER, loaders),)
                options['loaders'] = loaders


# Do it all function

def update_settings(name,
                    local_settings_file=None,
                    secret_key_file=None,
                    env_prefix=None,
                    apps_option=None,
                    processors_option=None,
                    quiet=False,
                    ):
    """
    Do all the updates for settings dictionary.
    """
    settings = SettingsDict.ensure(name)

    update_settings_from_module(settings, local_settings_file or DEFAULT_LOCAL_SETTINGS_FILE, quiet=quiet)
    update_secret_from_file(settings, secret_key_file=secret_key_file)
    update_settings_from_environment(settings, env_prefix=env_prefix, quiet=quiet)
    update_installed_apps(settings, apps_option=apps_option)
    update_context_processors_from_apps(settings, processors_option=processors_option)
    use_cache_template_loader_in_production(settings)
