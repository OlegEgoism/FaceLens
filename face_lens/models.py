from datetime import date
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractUser


class DateStamp(models.Model):
    """Временные отметки"""
    created = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated = models.DateTimeField(verbose_name='Дата изменения', auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser, DateStamp):
    """Пользователь"""
    username = models.CharField(verbose_name="Логин", max_length=150, unique=True, help_text="Обязательное поле. Не более 150 символов.", validators=[UnicodeUsernameValidator()], error_messages={"unique": "Пользователь с таким логином уже существует.", }, )
    avatar = models.ImageField(verbose_name='Аватар', max_length=500, upload_to='avatar', default='avatar/default/no_photo.png', blank=True, null=True)
    bio = models.TextField(verbose_name='Биография', null=True, blank=True)
    birthday = models.DateField(verbose_name='Дата рождения', null=True, blank=True)
    phone = models.CharField(verbose_name="Телефон", max_length=15, blank=True, null=True)
    phone_country = models.CharField(verbose_name="Страна", max_length=10, blank=True, null=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username

    def get_age_display(self):
        if not self.birthday:
            return None
        today = date.today()
        years = today.year - self.birthday.year
        months = today.month - self.birthday.month
        if today.day < self.birthday.day:
            months -= 1
        if months < 0:
            years -= 1
            months += 12
        return f"{years} лет, {months} мес."


class Photo(DateStamp):
    """Фотография с анализом лица"""
    user = models.ForeignKey(User, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(verbose_name='Фотография', upload_to='photos/%Y/%m/%d/')
    estimated_age = models.PositiveSmallIntegerField(verbose_name='Оценка возраста', null=True, blank=True)
    skin_health_score = models.DecimalField(verbose_name='Оценка кожи', max_digits=4, decimal_places=2, null=True, blank=True)
    wrinkles_score = models.DecimalField(verbose_name='Оценка морщин', max_digits=4, decimal_places=2, null=True, blank=True)
    mood = models.CharField(verbose_name='Настроение', max_length=50, blank=True)
    emotion_detected = models.CharField(verbose_name='Эмоция', max_length=50, blank=True)

    class Meta:
        verbose_name = 'Фотография'
        verbose_name_plural = 'Фотографии'
        unique_together = 'user', 'created'
        ordering = ('-created',)

    def __str__(self):
        return f"{self.user.username} — {self.created}"


class UserSettings(DateStamp):
    """Настройки"""
    user = models.ForeignKey(User, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='settings')
    auto_photo = models.BooleanField(verbose_name='Автоматическое фото', default=True)
    notify_time = models.TimeField(verbose_name='Времени автоматического фото', default='10:00:00')

    class Meta:
        verbose_name = 'Настройка'
        verbose_name_plural = 'Настройки'
        unique_together = 'user', 'auto_photo', 'notify_time'

    def __str__(self):
        return f"Автоматическое фото"
