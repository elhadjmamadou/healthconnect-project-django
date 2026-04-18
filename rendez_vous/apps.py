from django.apps import AppConfig


class RendezVousConfig(AppConfig):
    name = 'rendez_vous'
    verbose_name = 'Rendez-vous'

    def ready(self):
        import rendez_vous.signals  # noqa: F401
