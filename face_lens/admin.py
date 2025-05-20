from datetime import date

from django.contrib import admin
from django.utils.safestring import mark_safe

from face_lens.models import User, Photo, UserSettings, FaceAnalysis


class UserSettingsInline(admin.TabularInline):
    """Настройки пользователя"""
    model = UserSettings
    classes = ['collapse']
    extra = 0
    max_num = 10
    # can_delete = False


class PhotoInline(admin.TabularInline):
    """Фотография пользователя"""
    model = Photo
    classes = ['collapse']
    extra = 0
    max_num = 10
    can_delete = False
    readonly_fields = 'preview_image', 'image', 'created', 'updated'

    def preview_image(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="60" height="60" style="border-radius: 50%;" />')
        else:
            return 'Нет фотографии'

    preview_image.short_description = 'Фотография'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Пользователь"""
    fieldsets = (
        ('ЛИЧНЫЕ ДАННЫЕ', {
            'fields': ('username', 'preview_avatar', 'avatar', 'first_name', 'last_name', 'birthday', 'age_display', 'email', 'phone', 'phone_country', 'last_login', 'created', 'updated',)},),
        ('РАЗРЕШЕНИЯ', {
            'classes': ('collapse',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions',)}),
    )
    list_display = 'username', 'preview_avatar', 'first_name', 'last_name', 'birthday', 'age_display', 'email', 'phone', 'phone_country', 'last_login', 'created', 'updated', 'is_active', 'is_staff',
    list_filter = 'phone_country', 'is_staff', 'is_active', 'last_login', 'created', 'updated',
    list_editable = 'is_active',
    search_fields = 'username', 'email', 'phone',
    search_help_text = 'Поиск по логину, адресу электронной почты и номеру телефона'
    readonly_fields = 'age_display', 'last_login', 'created', 'updated', 'preview_avatar',
    date_hierarchy = 'date_joined'
    inlines = UserSettingsInline, PhotoInline,  # TimerPhotoInline
    list_per_page = 20

    def preview_avatar(self, obj):
        if obj.avatar:
            return mark_safe(f'<img src="{obj.avatar.url}" width="60" height="60" style="border-radius: 50%;" />')
        else:
            return 'Нет фотографии'

    preview_avatar.short_description = 'Аватар'

    def save_model(self, request, obj, form, change):
        """Проверка, есть ли еще один пользователь с таким же адресом электронной почты"""
        if obj.email:
            if User.objects.filter(email=obj.email).exclude(pk=obj.pk).exists():
                self.message_user(request, "Этот адрес электронной почты уже связан с другим аккаунтом", level='ERROR')
                return
        super().save_model(request, obj, form, change)

    def age_display(self, obj):
        return obj.get_age_display() or '—'
    age_display.short_description = 'Возраст'


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    """Фотография пользователя"""
    list_display = 'user', 'preview_image', 'created', 'updated'
    # readonly_fields = 'user', 'preview_image', 'image', 'created', 'updated',
    date_hierarchy = 'created'
    list_filter = 'user', 'created',
    list_per_page = 20

    def preview_image(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="60" height="60" style="border-radius: 0%;" />')
        else:
            return 'Нет фотографии'

    preview_image.short_description = 'Фотография'


@admin.register(FaceAnalysis)
class FaceAnalysisAdmin(admin.ModelAdmin):
    list_display = 'get_username', 'preview_image', 'estimated_age', 'skin_health_score', 'wrinkles_score', 'acne_score', 'mood', 'emotion_detected', 'created', 'updated',

    def get_username(self, obj):
        return obj.photo.user.username

    get_username.short_description = 'Пользователь'
    get_username.admin_order_field = 'photo__user__username'

    def preview_image(self, obj):
        if obj.photo.image:
            return mark_safe(f'<img src="{obj.photo.image.url}" width="60" height="60" style="border-radius: 0%;" />')
        return 'Нет фотографии'

    preview_image.short_description = 'Фотография'
