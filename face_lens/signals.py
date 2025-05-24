from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import time
from .models import User, UserSettings


@receiver(post_save, sender=User)
def create_default_settings(sender, instance, created, **kwargs):
    if created:
        times = [time(10, 0), time(14, 0), time(18, 0), time(20, 0)]
        for t in times:
            UserSettings.objects.get_or_create(
                user=instance,
                auto_photo=True,
                notify_time=t
            )
