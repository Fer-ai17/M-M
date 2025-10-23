from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # import signals to ensure they are registered
        try:
            import core.signals  # noqa: F401
        except Exception:
            pass
