from django.contrib import admin
from django.utils.safestring import mark_safe

from face_lens.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Пользователь"""
    fieldsets = (
        ('ЛИЧНЫЕ ДАННЫЕ', {
            'fields': ('username', 'avatar', 'email', 'phone', 'phone_country', 'last_login', 'date_joined',)},),
        ('РАЗРЕШЕНИЯ', {
            'classes': ('collapse',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions',)}),
    )
    list_display = 'username', 'preview_avatar', 'first_name', 'last_name', 'email', 'phone', 'phone_country', 'last_login', 'is_active', 'is_staff',
    list_filter = 'phone_country', 'is_staff', 'is_active', 'last_login', 'date_joined',
    list_editable = 'is_active',
    search_fields = 'username', 'email', 'phone',
    search_help_text = 'Поиск по логину, адресу электронной почты и номеру телефона'
    readonly_fields = 'last_login', 'date_joined', 'preview_avatar',
    date_hierarchy = 'date_joined'
    list_per_page = 20

    def preview_avatar(self, obj):
        if obj.avatar:
            return mark_safe(f'<img src="{obj.avatar.url}" width="60" height="60" style="border-radius: 50%;" />')
        else:
            return 'Нет фотографии'

    preview_avatar.short_description = 'Фотография'

    def save_model(self, request, obj, form, change):
        """Проверка, есть ли еще один пользователь с таким же адресом электронной почты"""
        if obj.email:
            if User.objects.filter(email=obj.email).exclude(pk=obj.pk).exists():
                self.message_user(request, "Этот адрес электронной почты уже связан с другим аккаунтом", level='ERROR')
                return
        super().save_model(request, obj, form, change)

