from os import environ
from os.path import basename, dirname, isfile, join as join_path, splitext
from sys import stderr
from collections import Iterable, OrderedDict, defaultdict
from itertools import chain
from json import loads as json_loads

from .utils.conf import (
    ensure_app_configs,
    create_secret_key_file,
    flatten_loaders,
    SettingsDict,
)
from .utils.importing import (
    find_file,
    file_path_from_module_name,
    find_and_import_module,
    load_module_from_file,
    unload_module,
)
from .utils import (
    unique,
    warning,
)


__all__ = [
    'update_settings_from_module',
    'update_settings_with_file',
    'update_secret_from_file',
    'update_settings_from_environment',
    'update_installed_apps',
    'update_context_processors_from_apps',
    'use_cache_template_loader_in_production',

    'update_settings',
    'update_settings_fixes',
]


DEFAULT_REQUIRED_APPS_OPTION = 'required_apps'
DEFAULT_CONTEXT_PROCESSORS_OPTION = 'context_processors'
DEFAULT_TEMPLATE_BACKEND = 'django.template.backends.django.DjangoTemplates'
DEFAULT_ENVIRONMENT_PREFIX = 'DJANGO_'
DEFAULT_CACHED_BACKENDS = ('django.template.backends.django.DjangoTemplates',)
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
        except ValueError: # json.JSONDecodeError (py 3.5+)
            if not quiet and setting_value and (
                setting_value[0] in '"{[0123456789' or
                setting_value.startswith('true') or
                setting_value.startswith('false')
            ):
                print("Warning: Failed to parse environment variable as JSON: {}='{}'".format(key, setting_value))

        setting = key[prefix_len:]
        settings[setting] = setting_value
        if not quiet:
            print("Note: defined settings.{} from environment".format(setting), file=stderr)


def update_settings_from_module(settings, module_name, search_base=None, quiet=False):
    """
    Update settings module with upper case values from another module.
    For example, can be used to include values from local_settings.py:
      `update_settings_from_module(__name__, 'local_settings')`.

    If search_base is None, then search will start from peer of __name__:
      e.g. `myapp.local_settings`, `local_settings`
    If sarch_base is string, then it's parsed as module path:
      `myapp.foo` -> `myapp.foo.local_settings`, `myapp.local_settings`, `local_settings`
    """
    settings = SettingsDict.ensure(settings)
    if search_base is None:
        search_base = settings.name.rpartition('.')[0]
    module, tried = find_and_import_module(module_name, search=search_base)

    if module:
        data = {setting: getattr(module, setting) for setting in dir(module) if setting.isupper()}
        settings.update(data)
        unload_module(module) # module can be removed from the memory as all values have been loaded
        del module
        return len(data)
    elif not quiet:
        warning("Couldn't find {}. Tried: {}".format(module_name, tried))
    return 0


def update_settings_with_file(settings, filename, search_path=None, quiet=False):
    """
    Update settings module with upper case values from another module.
    Another module is referenced with absolute or relative filename.
    Before executing another module, it's globals will be initialized with values
    from settings. Thus, you could just write `INSTALLED_APPS.append('my_app')`.

    For example, this can be used to include values from local_settings.py:
      `update_settings_with_file(__name__, 'local_settings')`.

    If filenmae is not path (no / in it), then search_path is used to find the file.
    If search_path is None, then directory of settings and it's parent is searched.
    """
    settings = SettingsDict.ensure(settings)

    if '/' not in filename:
        if not search_path:
            settings_dir = dirname(settings.file)
            search_path = [settings_dir, dirname(settings_dir)]
        if not filename.endswith('.py'):
            filename += '.py'
        file_ = find_file(filename, search_path)
        if file_ is None:
            if not quiet:
                warning("Couldn't find {}. Path: {}".format(filename, search_path))
            return
        filename = file_
    elif not isfile(filename):
        if not quiet:
            warning("File {} doesn't exist.".format(filename))
        return

    # load module with settings as globals
    name, _ = splitext(basename(filename))
    context = {setting: value for setting, value in settings.items() if setting.isupper()}
    module = load_module_from_file(name, filename, context=context)

    if module:
        # load values from the module
        data = {name: getattr(module, name) for name in dir(module) if name.isupper()}
        settings.update(data)
        # unload
        unload_module(module)
        del module
    elif not quiet:
        warning("Could not import {}".format(filename))


def update_secret_from_file(settings, secret_key_file=None, search_base=None, create_if_missing=True, setting=None):
    """
    Will update only a single value from a python module.

    By default this value is SECRET_KEY, but that can be changed with
    `setting` argument.

    If the module doesn't exists, then a new file is created unless
    `create_if_missing` is False.

    Module is searched starting at the peer of settings module. Alternative
    search path can be given with `search_base`.

    Argument `secret_key_file` can be a python module name or file path. File
    path can be used to import module from outside of project.
    """
    settings = SettingsDict.ensure(settings)
    secret_key_file = secret_key_file or DEFAULT_SECRET_KEY_FILE
    setting = setting or 'SECRET_KEY'

    if settings.get(setting):
        # We already have non null secret_key
        return

    if search_base is None:
        search_base = settings.name.rpartition('.')[0]

    direct_file = '/' in secret_key_file or secret_key_file.endswith('.py')

    if direct_file:
        name, _ = splitext(basename(secret_key_file))
        module = load_module_from_file(name, secret_key_file)
    else:
        module, _ = find_and_import_module(secret_key_file, search=search_base)

    if module:
        if hasattr(module, setting):
            settings[setting] = getattr(module, setting)
        else:
            warning("Setting {} was not found from {}.".format(setting, module.__file__))
        unload_module(module) # module can be removed from the memory as the value have been loaded
        del module
    elif create_if_missing:
        if not direct_file:
            secret_key_file = file_path_from_module_name(search_base, secret_key_file)
        try:
            key = create_secret_key_file(secret_key_file, setting=setting)
        except IOError as e:
            warning("Setting {} is not defined and we were unable to create {}: {}".format(setting, secret_key_file, e))
        else:
            print("Note: Stored setting {} in {}".format(setting, secret_key_file))
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


def use_cache_template_loader_in_production(settings, cached_backends=None):
    """
    Wrap template loaders with cached loader on production (DEBUG = False)
    """
    # FIXME: this is done by Django from version 1.11 onwards, thus drop this at some point
    settings = SettingsDict.ensure(settings)
    debug = settings.get('DEBUG', False)
    templates = settings.get('TEMPLATES')
    cached_backends = cached_backends or DEFAULT_CACHED_BACKENDS

    if not templates or debug:
        return

    for conf in templates:
        if conf['BACKEND'] in cached_backends:
            options = conf.setdefault('OPTIONS', {})
            loaders = options.get('loaders')
            if not loaders or DEFAULT_CACHED_LOADER not in flatten_loaders(loaders):
                if not loaders:
                    loaders = (DEFAULT_LOADER,)
                    if conf.get('APP_DIRS', False):
                        loaders += (DEFAULT_APP_LOADER,)
                loaders = ((DEFAULT_CACHED_LOADER, loaders),)
                options['loaders'] = loaders
                conf.pop('APP_DIRS')


# Do it all functions

def update_settings(name,
                    local_settings_file=None,
                    secret_key_file=None,
                    env_prefix=None,
                    apps_option=None,
                    processors_option=None,
                    cached_backends=None,
                    quiet=False,
                    ):
    """
    Do all the updates for settings dictionary.
    """
    settings = SettingsDict.ensure(name)

    update_settings_from_module(settings, local_settings_file or DEFAULT_LOCAL_SETTINGS_FILE, quiet=quiet)
    update_secret_from_file(settings, secret_key_file=secret_key_file)
    update_settings_from_environment(settings, env_prefix=env_prefix, quiet=quiet)

    update_settings_fixes(settings,
                          apps_option=apps_option,
                          processors_option=processors_option,
                          cached_backend=cached_backend,
                          )

def update_settings_fixes(settings,
                          apps_option=None,
                          processors_option=None,
                          cached_backends=None,
                          ):
    settings = SettingsDict.ensure(settings)
    update_installed_apps(settings, apps_option=apps_option)
    update_context_processors_from_apps(settings, processors_option=processors_option)
    use_cache_template_loader_in_production(settings, cached_backends=cached_backends)
