from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Document


class SchoolRegisterForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': 'Логин школы',
            'email': 'Email',
            'password1': 'Пароль',
            'password2': 'Подтверждение пароля',
        }


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ('title', 'file')
        labels = {
            'title': 'Название документа',
            'file': 'Файл',
        }
