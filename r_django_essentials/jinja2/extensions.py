from jinja2.ext import Extension


class I18nExtrasExtension(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        g = environment.globals

        from django.utils import translation
        g['get_current_language'] = translation.get_language


class CryptoExtension(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        g = environment.globals

        from django.utils.crypto import get_random_string
        g['get_random_string'] = get_random_string
