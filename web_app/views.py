from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DocumentForm, SchoolRegisterForm
from .models import Document


def register_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect('upload_documents')

    if request.method == 'POST':
        form = SchoolRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Аккаунт школы создан.')
            return redirect('upload_documents')
    else:
        form = SchoolRegisterForm()

    return render(request, 'registration/register.html', {'form': form})


@login_required
def upload_documents_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.school = request.user
            document.save()
            messages.success(request, 'Документ загружен.')
            return redirect('upload_documents')
    else:
        form = DocumentForm()

    documents = Document.objects.filter(school=request.user)
    return render(
        request,
        'web_app/upload.html',
        {
            'form': form,
            'documents': documents,
        },
    )


@login_required
def delete_document_view(request: HttpRequest, document_id: int) -> HttpResponse:
    document = get_object_or_404(Document, id=document_id, school=request.user)

    if request.method == 'POST':
        document.file.delete(save=False)
        document.delete()
        messages.success(request, 'Документ удалён.')

    return redirect('upload_documents')
