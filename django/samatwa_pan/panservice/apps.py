from django.apps import AppConfig

class PanserviceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'panservice'

    def ready(self):
        import panservice.signals