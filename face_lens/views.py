from django.contrib import messages
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.forms import modelformset_factory
from django.shortcuts import render, redirect, get_object_or_404

from django.forms import modelformset_factory
from face_lens.forms import UserRegistrationForm, UserUpdateForm, UserSettingsForm
from face_lens.models import  UserSettings


def home(request):
    """Главная страница"""
    return render(request, 'home.html')


def register(request):
    """Регистрация пользователя"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Ошибка в поле {form.fields[field].label}: {error}")
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def logout_view(request):
    """Выход пользователя"""
    logout(request)
    return redirect('home')


@login_required
def profile(request):
    """Профиль пользователя"""
    if request.method == 'POST' and 'avatar' in request.FILES:
        avatar = request.FILES['avatar']
        request.user.avatar = avatar
        request.user.save()
        return redirect('profile')
    return render(request, 'profile.html')


@login_required
def profile_edit(request):
    """Редактировать профиль пользователя"""
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Ошибка в поле '{field}': {error}")
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'profile_edit.html', {'form': form})





from django.db import IntegrityError
from django.forms import ValidationError

@login_required
def profile_settings(request):
    """Настройки профиля"""
    user = request.user
    SettingsFormSet = modelformset_factory(
        UserSettings,
        form=UserSettingsForm,
        extra=0,
        can_delete=False
    )
    queryset = UserSettings.objects.filter(user=user)
    if request.method == 'POST':
        formset = SettingsFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            try:
                formset.save()
                return redirect('home')
            except IntegrityError as e:
                # Добавляем общую ошибку к formset
                formset.non_form_errors().append(
                    "Ошибка: такие настройки уже существуют."
                )
                # Альтернативно можно добавить в formset._non_form_errors:
                formset._non_form_errors = formset.error_class([
                    "Такие настройки уже существуют!"
                ])
        else:
            print("Форма невалидна", formset.errors)
    else:
        formset = SettingsFormSet(queryset=queryset)
    return render(request, 'profile_settings.html', {'formset': formset})







from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required

PER_PAGE_OPTIONS = [1, 20, 50, 100]


@login_required
def profile_photos(request):
    per_page = request.GET.get('per_page', '10')
    try:
        per_page = int(per_page)
        if per_page not in PER_PAGE_OPTIONS:
            per_page = 10
    except ValueError:
        per_page = 10

    photos_list = Photo.objects.filter(user=request.user).select_related('analysis').order_by('-created')
    paginator = Paginator(photos_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'user_photos.html', {
        'page_obj': page_obj,
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
    })


import base64
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from .models import Photo


@login_required
def camera_photo_view(request):
    return render(request, 'camera_photo.html')


@login_required
def save_photo(request):
    if request.method == 'POST':
        image_data = request.POST.get('image_data')
        if image_data:
            format, imgstr = image_data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'photo_{request.user.id}_{timezone.now().strftime("%Y%m%d%H%M%S")}.{ext}')
            Photo.objects.create(user=request.user, image=data)
            return redirect('profile_photos')
    return redirect('camera_photo')


from deepface import DeepFace
from .models import FaceAnalysis
import shutil, tempfile
from pathlib import Path
import cv2
import numpy as np

# Словарь перевода
EMOTION_TRANSLATIONS = {
    "happy": "Счастье",
    "sad": "Грусть",
    "angry": "Злость",
    "surprise": "Удивление",
    "fear": "Страх",
    "disgust": "Отвращение",
    "neutral": "Нейтрально"
}


def estimate_skin_metrics(image_path, estimated_age, emotion):
    img = cv2.imread(image_path)
    img = cv2.resize(img, (224, 224))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    wrinkles_score = np.std(gray) / 10
    wrinkles_score = max(0, min(10, 10 - wrinkles_score))

    blur = cv2.GaussianBlur(gray, (9, 9), 0)
    acne_score = np.std(gray - blur) * 2
    acne_score = max(0, min(10, 10 - acne_score))

    base_score = 10 - (estimated_age or 30) / 10
    if emotion in ['sad', 'angry', 'disgust']:
        base_score -= 2
    skin_health_score = max(0, min(10, base_score))

    return round(skin_health_score, 2), round(wrinkles_score, 2), round(acne_score, 2)


@login_required
def analyze_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id, user=request.user)

    try:
        original_path = photo.image.path

        # Временная копия файла
        tmp_dir = tempfile.mkdtemp()
        tmp_path = Path(tmp_dir) / Path(original_path).name
        shutil.copyfile(original_path, tmp_path)

        # Анализ лица
        result = DeepFace.analyze(img_path=str(tmp_path), actions=['age', 'emotion'], enforce_detection=False)[0]
        age = result['age']
        emotion = result['dominant_emotion']
        emotion_rus = EMOTION_TRANSLATIONS.get(emotion, emotion.capitalize())

        # Эвристическая оценка кожи
        skin_health_score, wrinkles_score, acne_score = estimate_skin_metrics(str(tmp_path), age, emotion)

        # Сохранение анализа
        FaceAnalysis.objects.update_or_create(
            photo=photo,
            defaults={
                "estimated_age": age,
                "emotion_detected": emotion_rus,
                "mood": emotion_rus,
                "health_comment": f"Анализ выполнен автоматически: {emotion_rus.lower()}",
                "skin_health_score": skin_health_score,
                "wrinkles_score": wrinkles_score,
                "acne_score": acne_score,
            }
        )
        messages.success(request, "Анализ успешно выполнен.")
    except Exception as e:
        messages.error(request, f"Ошибка анализа: {e}")

    return redirect("profile_photos")
