from django.apps import AppConfig


class FaceLensConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'face_lens'
    verbose_name = "Фотоанализ лица"


    def ready(self):
        import face_lens.signals
