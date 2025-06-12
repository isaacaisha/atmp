from django.apps import AppConfig


class AtmpAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'atmp_app'
    
    def ready(self):
        import atmp_app.signals 
