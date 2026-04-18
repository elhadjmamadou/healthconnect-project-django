from django.apps import AppConfig


class ConsultationsConfig(AppConfig):
    name = 'consultations'
    verbose_name = 'Consultations'

    def ready(self):
        import consultations.signals  # noqa: F401
