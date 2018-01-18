
try:
    from django.core.management.utils import get_random_secret_key
except ImportError:
    from django.utils.crypto import get_random_string
    def get_random_secret_key():
        """
        Generate random string used as secret key.
        Uses django.utils.crypto.get_random_string
        """
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        return get_random_string(50, chars)
