from django.apps import AppConfig


class ECommerceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'E_commerce'

    def ready(self):
        import E_commerce.models
