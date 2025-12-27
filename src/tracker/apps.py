from django.apps import AppConfig


class TrackerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.tracker"

    def ready(self):
        import src.tracker.signals  # noqa: F401
