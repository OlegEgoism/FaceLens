from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from face_lens.views import home, logout_view, register, profile, profile_edit, profile_settings, camera, profile_photos, camera_save, analyze_photo, delete_photo

urlpatterns = [
    path('admin/', admin.site.urls),  # Админка

    path('', home, name='home'),
    path('register/', register, name='register'),  # Регистрация пользователя
    path('login/', auth_views.LoginView.as_view(), name='login'),  # Вход пользователя
    path('logout/', logout_view, name='logout'),  # Выход пользователя

    path('profile/', profile, name='profile'),  # Профиль
    path('profile/edit/', profile_edit, name='profile_edit'),  # Редактировать профиль
    path('profile/settings/', profile_settings, name='profile_settings'),  # Настройки
    path('profile/photos/', profile_photos, name='profile_photos'),  # Фото альбом
    path('profile/photo/<int:photo_id>/analyze/', analyze_photo, name='analyze_photo'),  # Анализ фото
    path('profile/photo/<int:photo_id>/delete/', delete_photo, name='delete_photo'),  # Удалить фото

    path('camera', camera, name='camera'),  # Камера
    path('camera_save/', camera_save, name='camera_save'),  # Сделать фото

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
