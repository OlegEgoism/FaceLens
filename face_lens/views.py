from django.contrib import messages
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from face_lens.forms import UserRegistrationForm, UserUpdateForm


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
    if request.method == 'POST' and 'avatar' in request.FILES:
        avatar = request.FILES['avatar']
        request.user.avatar = avatar
        request.user.save()
        return redirect('profile')
    return render(request, 'profile.html')


@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'profile_edit.html', {'form': form})
