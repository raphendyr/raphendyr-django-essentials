Essential Django utilities from Raphendyr
=========================================

Few essential additions for working with Django web framework.
In other words, stuff I have always copied to every project I have been working with.


Setting management
------------------

Module :code:`conf` contains tools to hwlp working with django :code:`settings.py`.
Most important parts are including :code:`local_settings.py` and creating :code:`SECRET_KEY` in :code:`secret_key.py`.
In addition, environment variables starting with :code:`DJANGO_` will be included (parsed as json) to overwrite settings (useful for heroku for example).

In end of your :code:`settings.py` add following:

.. code-block:: python

  from r_django_essentials.conf import update_settings
  update_settings(__name__)

That is basically same as:

.. code-block:: python

  from r_django_essentials.conf import *

  # second argument is optional for all except firts. Default is shown here.
  update_settings_from_module(__name__, 'local_settings')
  update_secret_from_file(__name__, 'secret_key')
  update_settings_from_environment(__name__, 'DJANGO_')
  update_installed_apps(__name__, 'required_apps')
  update_context_processors_from_apps(__name__, 'context_processors')
  use_cache_template_loader_in_production(__name__)

Consult the :code:`conf.py` for more details.


Secret key autogeneration
-------------------------

Every installation of your application should always use it's own randomly generated :code:`SECRET_KEY`.
To help with this task you can use this feature to automatically create new key if one is not provided by the settings.

For this feature to work, your :code:`settings.py` needs to do one of the following:

.. code-block:: python

  # Include SECRET_KEY from secret_key.py into settings
  from r_django_essentials.conf import update_secret_from_file
  update_secret_from_file(__name__, 'secret_key')

.. code-block:: python

  # update_settings will call above function as part of it's work
  from r_django_essentials.conf import update_settings
  update_settings(__name__)

This will load the option if the file exists and will create new file if one doesn't exist.

Remember to add :code:`myproject/secret_key.py` to :code:`.gitignore` as you shouldn't ever have :code:`SECRET_KEY` in your version control.


Django app dependencies
-----------------------

Django doesn't support depending from another Django app, but that is still sometimes really useful.
To keep power for the web app maintainer, don't abuse this system my including complex django apps.
This feature is best used to include template and asset libraries (distributed ass django apps).

For this feature to work, your :code:`settings.py` needs to do one of the following:

.. code-block:: python

  # Just expand the apps dependencies
  from r_django_essentials.conf import expand_required_apps
  INSTALLED_APPS = expand_required_apps(INSTALLED_APPS)

.. code-block:: python

  # Do same as above, but manipulate settings module
  from r_django_essentials.conf import update_installed_apps
  update_installed_apps(__name__)

.. code-block:: python

  # update_settings will call above function as part of it's work
  from r_django_essentials.conf import update_settings
  update_settings(__name__)

Now that :code:`settings.py` is calling correct functions, you need to add something like following to your apps :code:`AppConfig`:

.. code-block:: python

  # myapp/apps.py
  from django.apps import AppConfig

  class MyAppConfig(AppConfig):
      name = 'myapp'
      verbose_name = 'My example app'

      required_apps = [
          'django.contrib.staticfiles',
          'django.contrib.humanize',
      ]

Those apps will be added to :code:`INSTALLED_APPS` by one of the above settings snippets.


Required context processors
---------------------------

Similar to app dependencies, this feature populates template engines :code:`context_processors` list from :code:`AppConfig`.

For this feature to work, your :code:`settings.py` needs to do one of the following:

.. code-block:: python

  # Just update TEMPLATES list of dictionaries
  from r_django_essentials.conf import add_required_context_processors
  add_required_context_processors(TEMPLATES, INSTALLED_APPS)

.. code-block:: python

  # Do same as above, but manipulate settings module
  from r_django_essentials.conf import update_context_processors_from_apps
  update_context_processors_from_apps(__name__)

.. code-block:: python

  # update_settings will call above function as part of it's work
  from r_django_essentials.conf import update_settings
  update_settings(__name__)

In your apps :code:`AppConfig` you would have something like this:

.. code-block:: python

  # myapp/apps.py
  from django.apps import AppConfig

  class MyAppConfig(AppConfig):
      name = 'myapp'
      verbose_name = 'My example app'

      context_processors = 'myapp.context_processors.myapp_context_processor' 
      # or
      context_processors = (
          'myapp.context_processors.myapp_context_processor1',
          'myapp.context_processors.myapp_context_processor2',
      )

Above will add context processors into django template engines options.
If you need to add context processors for different backend,
then use dictionary with backend as a key and list of processors as value.


Deprecated warning
------------------

Need to mark function deprecated without good deprecation system in place?

.. code-block:: python

  from r_django_essentials.deprecation import deprecated

  @deprecated("my_function is deprecated, use my_new_function instead")
  def my_function(argument):
      return my_new_function(argument)


Colorized log formatter
-----------------------

You would like to color code different log sources with different colors?

In your :code:`settings.py`:

.. code-block:: python

  OGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
      'colored': {
        '()': 'r_django_essentials.logging.SourceColorizeFormatter',
        'format': '[%(asctime)s: %(levelname)8s %(name)s] %(message)s',
        'colors': {
          'django.db.backends': {'fg': 'cyan'},
          'myapp': {'fg': 'red'},
        },
      },
    },
    'handlers': {
      'debug_console': {
        'level': 'DEBUG',
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stdout',
        'formatter': 'colored',
      },
    },
    'loggers': {
      '': {
        'level': 'DEBUG',
        'handlers': ['debug_console'],
        'propagate': True
      },
    },
  }


Enum for choices in models
--------------------------

Easily create enumerations that works well with choices field in django.

In your :code:`models.py`:

.. code-block:: python

  from django.db import models
  from django.utils.translation import ugettext_lazy as _
  from r_django_essentials.fields import Enum

  class MyProcess(models.Model):
      STATUS = Enum(
          ('OK', 0, _('Process is ok')),
          ('PROBLEM', 1, _('Process has problem')),
          ('ERROR', 2, _('Process is in error state')),
      )

      status = models.PositiveSmallIntegerField(
          default=STATUS.OK,
          choices=STATUS.choices,
          verbose_name=_("Process status"),
      )

      @property
      def status_text(self):
          return self.STATUS[self.status]
