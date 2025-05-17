from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile


class DateStamp(models.Model):
    """Временные отметки"""
    created = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated = models.DateTimeField(verbose_name='Дата изменения', auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser, DateStamp):
    """Пользователь"""
    username = models.CharField(verbose_name="Логин", max_length=150, unique=True, help_text="Обязательное поле. Не более 150 символов.", validators=[UnicodeUsernameValidator()], error_messages={"unique": "Пользователь с таким логином уже существует.", }, )
    avatar = models.ImageField(verbose_name='Аватар', upload_to='avatar', default='avatar/default/no_photo.png', blank=True, null=True)
    bio = models.TextField(verbose_name='Биография', null=True, blank=True)
    birthday = models.DateField(verbose_name='Дата рождения', null=True, blank=True)
    phone = models.CharField(verbose_name="Телефон", max_length=15, blank=True, null=True)
    phone_country = models.CharField(verbose_name="Страна", max_length=10, blank=True, null=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        if self.avatar:
            img = Image.open(self.avatar)
            if img.mode not in ('L', 'RGB', 'RGBA'):
                img = img.convert('RGB')
            img = img.resize((400, 400), Image.ANTIALIAS)
            buffer = BytesIO()
            img.save(buffer, format='JPEG')
            buffer.seek(0)
            self.avatar.save(self.avatar.name, ContentFile(buffer.read()), save=False)
        super().save(*args, **kwargs)


class Photo(DateStamp):
    """Фотография"""
    user = models.ForeignKey(User, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(verbose_name='Фотография', upload_to='photos/%Y/%m/%d/')

    class Meta:
        verbose_name = 'Фотография'
        verbose_name_plural = 'Фотографии'
        unique_together = 'user', 'created'
        ordering = '-created',

    def __str__(self):
        return f"{self.user.username} — {self.photo_date}"


class FaceAnalysis(DateStamp):
    """Анализ лица"""
    photo = models.OneToOneField(Photo, verbose_name='Фотография', on_delete=models.CASCADE, related_name='analysis')
    estimated_age = models.PositiveSmallIntegerField(verbose_name='Оценка возраста', null=True, blank=True)
    skin_health_score = models.DecimalField(verbose_name='Оценка состояние кожи', max_digits=4, decimal_places=2, null=True, blank=True)
    wrinkles_score = models.DecimalField(verbose_name='Оценка морщин', max_digits=4, decimal_places=2, null=True, blank=True)
    acne_score = models.DecimalField(verbose_name='Оценка угревой сыпи', max_digits=4, decimal_places=2, null=True, blank=True)
    mood = models.CharField(verbose_name='Настроение', max_length=50, blank=True)
    emotion_detected = models.CharField(verbose_name='Эмоция', max_length=50, blank=True)
    health_comment = models.TextField(blank=True, verbose_name='Комментарий пользователя')

    class Meta:
        verbose_name = 'Анализ лица'
        verbose_name_plural = 'Анализы лица'

    def __str__(self):
        return f"Анализ для {self.photo}"


class UserSettings(DateStamp):
    """Настройки пользователя"""
    user = models.OneToOneField(User, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='settings')
    auto_photo = models.BooleanField(verbose_name='Автоматическое фото', default=True)

    class Meta:
        verbose_name = 'Настройки пользователя'
        verbose_name_plural = 'Настройки пользователей'

    def __str__(self):
        return f"Настройки {self.user.username}"


class TimerPhoto(DateStamp):
    """Настройки времени"""
    user = models.ForeignKey(UserSettings, verbose_name='Настройки пользователя', on_delete=models.CASCADE, related_name='settings')
    notify_time = models.TimeField(verbose_name='Установка времени автоматического фото', default='10:00')

    class Meta:
        verbose_name = 'Настройка времени'
        verbose_name_plural = 'Настройки времени'

    def __str__(self):
        return f"Настройки {self.user.username}"
