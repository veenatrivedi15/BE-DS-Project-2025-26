from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """
        Import signals and other modules when the app is ready.
        """
        # Import pollution admin registration
        try:
            from . import pollution_admin
        except ImportError:
            pass
