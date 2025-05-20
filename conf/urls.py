"""
URL configuration for conf project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from face_lens.views import home, logout_view, register, profile, profile_edit, profile_settings, profile_photos, camera_photo_view, save_photo, analyze_photo  # , profile_photos

urlpatterns = [
    path('admin/', admin.site.urls),  # Админка

    path('', home, name='home'),
    path('register/', register, name='register'),  # Регистрация пользователя
    path('login/', auth_views.LoginView.as_view(), name='login'),  # Вход пользователя
    path('logout/', logout_view, name='logout'),  # Выход пользователя
    path('profile/', profile, name='profile'),  # Профиль
    path('profile/edit/', profile_edit, name='profile_edit'),  # Редактировать профиль
    path('profile/settings/', profile_settings, name='profile_settings'),  # Настройки профиля
    path('profile/photos/', profile_photos, name='profile_photos'),

    path('photo/camera/', camera_photo_view, name='camera_photo'),
    path('photo/camera/save/', save_photo, name='save_photo'),
    path('photo/<int:photo_id>/analyze/', analyze_photo, name='analyze_photo'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
