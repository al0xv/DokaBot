from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем валидацию расширения файла
        self.fields['file'].validators.append(
            FileExtensionValidator(
                allowed_extensions=['pdf', 'txt', 'doc', 'docx'],
                message='Разрешены только файлы PDF, TXT, DOC, DOCX.'
            )
        )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Проверка размера файла (максимум 50MB)
            if file.size > 50 * 1024 * 1024:
                raise forms.ValidationError('Размер файла не должен превышать 50MB.')
            # Проверка что файл не пустой
            if file.size == 0:
                raise forms.ValidationError('Нельзя загрузить пустой файл.')
        return file
