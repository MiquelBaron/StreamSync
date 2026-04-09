from django.apps import AppConfig


class SsConfig(AppConfig):
    name = 'ss'

    def ready(self):
        import ss.signals  # noqa: F401
