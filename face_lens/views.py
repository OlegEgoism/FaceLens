import base64
from django.contrib import messages
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.forms import modelformset_factory
from django.forms.utils import ErrorList
from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError
from matplotlib.ticker import MaxNLocator

from face_lens.forms import UserRegistrationForm, UserUpdateForm, UserSettingsForm
from face_lens.models import UserSettings, Photo
from django.utils import timezone
from django.core.files.base import ContentFile
from deepface import DeepFace
import shutil, tempfile
from pathlib import Path
import cv2
import numpy as np
from datetime import datetime, date
import matplotlib.pyplot as plt
import io

PER_PAGE_OPTIONS = [20, 50, 100]
EMOTION_TRANSLATIONS = {
    "happy": "Счастье",
    "sad": "Грусть",
    "angry": "Злость",
    "surprise": "Удивление",
    "fear": "Страх",
    "disgust": "Отвращение",
    "neutral": "Нейтрально"
}


def home(request):
    """Главная страница"""
    user = request.user
    return render(request, 'home.html', {'user': user})


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
    user = request.user
    all_photos = Photo.objects.filter(user=user).count()
    if request.method == 'POST' and 'avatar' in request.FILES:
        avatar = request.FILES['avatar']
        request.user.avatar = avatar
        request.user.save()
        return redirect('profile')
    return render(request, 'profile/profile.html', {'all_photos': all_photos})


@login_required
def clear_photos(request):
    """Очистить все фото пользователя"""
    user = request.user
    if request.method == 'POST':
        Photo.objects.filter(user=user).delete()
        messages.success(request, "Все фото успешно удалены.")
        return redirect('profile_photos')
    return render(request, 'profile/clear_photos.html')


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

    photos_list = Photo.objects.filter(user=request.user)

    # Фильтры из запроса
    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')
    emotion = request.GET.get('emotion')

    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
            photos_list = photos_list.filter(created__date__gte=date_from)
        except ValueError:
            pass
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d")
            photos_list = photos_list.filter(created__date__lte=date_to)
        except ValueError:
            pass

    if emotion and emotion != "all":
        photos_list = photos_list.filter(emotion_detected__iexact=emotion)

    photos_list = photos_list.order_by('-created')

    paginator = Paginator(photos_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    user = request.user

    def get_real_age(user):
        if not user.birthday:
            return None
        today = date.today()
        years = today.year - user.birthday.year
        if (today.month, today.day) < (user.birthday.month, user.birthday.day):
            years -= 1
        return years

    real_age = get_real_age(user)

    # Получаем уникальные, нормализованные значения эмоций
    emotions_raw = Photo.objects.filter(user=user).values_list('emotion_detected', flat=True)
    emotions_clean = set(e.strip().lower() for e in emotions_raw if e)

    # Формируем список кортежей (ключ, перевод)
    emotions_for_filter = []
    for key in sorted(emotions_clean):
        # Ищем в словаре с ключом в нижнем регистре
        translation = EMOTION_TRANSLATIONS.get(key)
        if not translation:
            # Если нет перевода, берем ключ с заглавной буквы
            translation = key.capitalize()
        emotions_for_filter.append((key, translation))

    return render(request, 'profile/profile_photos.html', {
        'page_obj': page_obj,
        'per_page': per_page,
        'per_page_options': PER_PAGE_OPTIONS,
        'real_age': real_age,
        'filters': {
            'date_from': date_from_str or '',
            'date_to': date_to_str or '',
            'emotion': emotion or 'all',
        },
        'emotions_for_filter': emotions_for_filter,
    })


@login_required
def delete_photo(request, photo_id):
    """Удалить фото"""
    photo = get_object_or_404(Photo, id=photo_id, user=request.user)
    if request.method == 'POST':
        photo.delete()
    return redirect('profile_photos')


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
                photo.skin_health_score = skin_health_score
                photo.wrinkles_score = wrinkles_score
                photo.save()
            except Exception as e:
                print("Ошибка анализа:", e)
                messages.error(request, f"Ошибка анализа: {e}")
            return redirect('profile_photos')
    return redirect('camera_photo')


@login_required
def analysis(request):
    user = request.user

    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')
    emotion_filter = request.GET.get('emotion')

    photos = Photo.objects.filter(user=user, estimated_age__isnull=False)

    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
            photos = photos.filter(created__date__gte=date_from)
        except ValueError:
            date_from = None
    else:
        date_from = None

    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d")
            photos = photos.filter(created__date__lte=date_to)
        except ValueError:
            date_to = None
    else:
        date_to = None

    # Фильтрация по эмоции — ПО ПЕРЕВОДУ!
    if emotion_filter and emotion_filter != "all":
        photos = photos.filter(emotion_detected=emotion_filter)
    photos = photos.order_by('created')

    if not photos.exists() or not user.birthday:
        return render(request, 'profile/analysis.html', {
            'error': "Необходимо указать свой возраст в профиле.",
            'date_from': date_from_str or '',
            'date_to': date_to_str or '',
            'emotion_filter': emotion_filter or 'all',
            'emotion_options': list(EMOTION_TRANSLATIONS.values()),
        })
    today = date.today()
    user_age_years = today.year - user.birthday.year - ((today.month, today.day) < (user.birthday.month, user.birthday.day))
    photo_dates = [photo.created.strftime("%d.%m.%Y") for photo in photos]
    photo_ages = [photo.estimated_age for photo in photos]
    avg_age = round(sum(photo_ages) / len(photo_ages), 1) if photo_ages else None

    plt.figure(figsize=(6, 4))
    plt.plot(photo_dates, photo_ages, marker='o', color='blue')
    plt.axhline(y=user_age_years, color='green', linestyle='--')
    plt.ylabel("Возраст (лет)")
    plt.legend()
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.xticks(rotation=45)
    plt.tight_layout()
    buffer1 = io.BytesIO()
    plt.savefig(buffer1, format='png')
    buffer1.seek(0)
    graphic1 = base64.b64encode(buffer1.getvalue()).decode('utf-8')
    plt.close()

    # График эмоций
    emotions = [photo.emotion_detected or '—' for photo in photos]
    plt.figure(figsize=(6, 4))
    plt.plot(photo_dates, emotions, marker='o', color='orange')
    plt.xticks(rotation=45)
    plt.tight_layout()
    buffer3 = io.BytesIO()
    plt.savefig(buffer3, format='png')
    buffer3.seek(0)
    graphic2 = base64.b64encode(buffer3.getvalue()).decode('utf-8')
    plt.close()

    return render(request, 'profile/analysis.html', {
        'graphic1': graphic1,
        'graphic2': graphic2,
        'avg_age': avg_age,
        'user_age': user_age_years,
        'error': None,
        'date_from': date_from_str or '',
        'date_to': date_to_str or '',
        'emotion_filter': emotion_filter or 'all',
        'emotion_options': list(EMOTION_TRANSLATIONS.values()),
    })
