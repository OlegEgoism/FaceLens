import phonenumbers
from django import forms
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from face_lens.models import User, UserSettings

class UserRegistrationForm(UserCreationForm):
    """Регистрация пользователя"""
    contact = forms.CharField(
        required=True,
        label="Почта или телефон",
        help_text="Введите email (с @) или номер телефона"
    )
    photo = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = "username", "first_name", "last_name", "contact", "password1", "password2"

    def clean(self):
        cleaned_data = super().clean()
        contact = cleaned_data.get('contact')

        if not contact:
            self.add_error('contact', "Поле обязательно для заполнения.")
            return cleaned_data

        # Email
        if '@' in contact:
            try:
                validate_email(contact)
            except ValidationError:
                self.add_error('contact', "Некорректный формат email.")
                return cleaned_data

            if User.objects.filter(email=contact).exists():
                self.add_error('contact', "Почта уже используется.")
            else:
                cleaned_data['email'] = contact

        # Телефон
        else:
            try:
                phone_number = phonenumbers.parse(contact, region=None)
                if not phonenumbers.is_valid_number(phone_number):
                    raise ValidationError("Неверный номер телефона.")
            except Exception:
                self.add_error('contact', "Некорректный формат телефона.")
                return cleaned_data

            formatted_number = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)
            if User.objects.filter(phone=formatted_number).exists():
                self.add_error('contact', "Телефон уже используется.")
            else:
                cleaned_data['phone'] = formatted_number
                region_code = phonenumbers.region_code_for_number(phone_number)
                cleaned_data['phone_country'] = region_code  # <- сохраняем код страны

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        contact = self.cleaned_data.get('contact')

        if '@' in contact:
            user.email = contact
        else:
            phone_number = phonenumbers.parse(contact, region=None)
            formatted_number = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)
            region_code = phonenumbers.region_code_for_number(phone_number)

            user.phone = formatted_number
            user.phone_country = region_code

        if commit:
            user.save()
        return user




class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'birthday', 'bio')
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            try:
                phone_number = phonenumbers.parse(phone, region=None)
                if not phonenumbers.is_valid_number(phone_number):
                    raise ValidationError("Неверный номер телефона.")
            except Exception:
                raise ValidationError("Некорректный формат телефона.")

            formatted_number = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)
            self.cleaned_data['phone'] = formatted_number
            self.cleaned_data['phone_country'] = phonenumbers.region_code_for_number(phone_number)
        else:
            self.cleaned_data['phone_country'] = None

        return self.cleaned_data['phone']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.phone_country = self.cleaned_data.get('phone_country', None)
        if commit:
            user.save()
        return user



class UserSettingsForm(forms.ModelForm):
    """Настройки профиля"""

    class Meta:
        model = UserSettings
        fields = 'auto_photo', 'notify_time'
        widgets = {
            'notify_time': forms.TimeInput(format='%H:%M:%S', attrs={'type': 'time'}),
        }
