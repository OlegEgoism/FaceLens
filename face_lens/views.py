import base64
from django.contrib import messages
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.forms import modelformset_factory
from django.forms.utils import ErrorList
from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError
from face_lens.forms import UserRegistrationForm, UserUpdateForm, UserSettingsForm
from face_lens.models import UserSettings, Photo
from django.utils import timezone
from django.core.files.base import ContentFile
from deepface import DeepFace
import shutil, tempfile
from pathlib import Path
import cv2
import numpy as np

PER_PAGE_OPTIONS = [20, 50, 100]


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
    return render(request, 'profile/profile.html')


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
    return render(request, 'profile/profile_edit.html', {'form': form})


@login_required
def profile_settings(request):
    """Настройки"""
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
            instances = formset.save(commit=False)
            try:
                for instance in instances:
                    if not instance.user_id:
                        instance.user = user
                    instance.save()
                return redirect('home')
            except IntegrityError:
                formset._non_form_errors = ErrorList([
                    "Такие настройки уже существуют! Проверьте, что вы не дублируете записи."
                ])
        else:
            print("Форма невалидна", formset.errors)
    else:
        formset = SettingsFormSet(queryset=queryset)
    return render(request, 'profile/profile_settings.html', {'formset': formset})


@login_required
def profile_photos(request):
    """Фото альбом"""
    per_page = request.GET.get('per_page', '10')
    try:
        per_page = int(per_page)
        if per_page not in PER_PAGE_OPTIONS:
            per_page = 20
    except ValueError:
        per_page = 20
    photos_list = Photo.objects.filter(user=request.user).order_by('-created')
    paginator = Paginator(photos_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'profile/profile_photos.html', {
        'page_obj': page_obj,
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
    })


@login_required
def delete_photo(request, photo_id):
    """Удалить фото"""
    photo = get_object_or_404(Photo, id=photo_id, user=request.user)
    if request.method == 'POST':
        photo.delete()
    return redirect('profile_photos')


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
    """Оценка фото"""
    img = cv2.imread(image_path)
    img = cv2.resize(img, (224, 224))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    wrinkles_score = np.std(gray) / 10
    wrinkles_score = max(0, min(10, 10 - wrinkles_score))
    blur = cv2.GaussianBlur(gray, (9, 9), 0)
    base_score = 10 - (estimated_age or 30) / 10
    if emotion in ['sad', 'angry', 'disgust']:
        base_score -= 2
    skin_health_score = max(0, min(10, base_score))
    return round(skin_health_score, 2), round(wrinkles_score, 2)


@login_required
def analyze_photo(request, photo_id):
    """Анализ фото"""
    photo = get_object_or_404(Photo, id=photo_id, user=request.user)
    try:
        original_path = photo.image.path
        tmp_dir = tempfile.mkdtemp()
        tmp_path = Path(tmp_dir) / Path(original_path).name
        shutil.copyfile(original_path, tmp_path)
        result = DeepFace.analyze(img_path=str(tmp_path), actions=['age', 'emotion'], enforce_detection=False)[0]
        age = result['age']
        emotion = result['dominant_emotion']
        emotion_rus = EMOTION_TRANSLATIONS.get(emotion, emotion.capitalize())
        skin_health_score, wrinkles_score = estimate_skin_metrics(str(tmp_path), age, emotion)
        photo.estimated_age = age
        photo.emotion_detected = emotion_rus
        photo.mood = emotion_rus
        photo.skin_health_score = skin_health_score
        photo.wrinkles_score = wrinkles_score
        photo.save()
        # messages.success(request, "Анализ успешно выполнен.")
    except Exception as e:
        messages.error(request, f"Ошибка анализа: {e}")
    return redirect("profile_photos")


@login_required
def camera(request):
    """Камера"""
    return render(request, 'camera.html')


@login_required
def camera_save(request):
    """Сделать фото и сразу выполнить анализ"""
    if request.method == 'POST':
        image_data = request.POST.get('image_data')
        if image_data:
            format, imgstr = image_data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'photo_{request.user.id}_{timezone.now().strftime("%Y%m%d%H%M%S")}.{ext}')
            photo = Photo.objects.create(user=request.user, image=data)

            try:
                original_path = photo.image.path
                tmp_dir = tempfile.mkdtemp()
                tmp_path = Path(tmp_dir) / Path(original_path).name
                shutil.copyfile(original_path, tmp_path)

                result = DeepFace.analyze(img_path=str(tmp_path), actions=['age', 'emotion'], enforce_detection=False)[0]
                age = result['age']
                emotion = result['dominant_emotion']
                emotion_rus = EMOTION_TRANSLATIONS.get(emotion, emotion.capitalize())
                skin_health_score, wrinkles_score = estimate_skin_metrics(str(tmp_path), age, emotion)

                photo.estimated_age = age
                photo.emotion_detected = emotion_rus
                photo.mood = emotion_rus
                photo.skin_health_score = skin_health_score
                photo.wrinkles_score = wrinkles_score
                photo.save()
            except Exception as e:
                print("Ошибка анализа:", e)
                messages.error(request, f"Ошибка анализа: {e}")
            return redirect('profile_photos')
    return redirect('camera_photo')




import matplotlib.pyplot as plt
import io
import base64
from datetime import date
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def age_analysis_chart(request):
    user = request.user
    photos = user.photos.filter(estimated_age__isnull=False).order_by('created')

    if not photos.exists() or not user.birthday:
        return render(request, 'profile/age_analysis.html', {
            'error': "Недостаточно данных для анализа."
        })

    # Реальный возраст пользователя
    today = date.today()
    user_age_years = today.year - user.birthday.year - ((today.month, today.day) < (user.birthday.month, user.birthday.day))

    # Подготовим данные
    photo_dates = [photo.created.strftime("%d.%m.%Y") for photo in photos]
    photo_ages = [photo.estimated_age for photo in photos]

    # Построим график
    plt.figure(figsize=(10, 5))
    plt.plot(photo_dates, photo_ages, marker='o', color='blue', label='Возраст по фото')
    plt.axhline(y=user_age_years, color='green', linestyle='--', label=f'Реальный возраст: {user_age_years}')

    plt.title("Сравнение возраста")
    plt.xlabel("Дата фото")
    plt.ylabel("Возраст (лет)")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Сохраним график в base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    graphic = base64.b64encode(image_png).decode('utf-8')

    return render(request, 'profile/age_analysis.html', {
        'graphic': graphic
    })
