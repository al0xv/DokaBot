from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from openai import OpenAIError

from .forms import DocumentForm
from .models import Document
from .services import remove_document_from_vector_store, sync_document_to_vector_store


@login_required
def upload_documents_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.school = request.user
            document.save()
            try:
                sync_document_to_vector_store(document)
            except (OSError, RuntimeError, OpenAIError) as exc:
                document.file.delete(save=False)
                document.delete()
                messages.error(request, f'Документ не загружен в датасет: {exc}')
            else:
                messages.success(request, 'Документ загружен и добавлен в датасет.')
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
        try:
            remove_document_from_vector_store(document)
            document.file.delete(save=False)
            document.delete()
            messages.success(request, 'Документ удалён из сайта и датасета.')
        except (OSError, RuntimeError, OpenAIError) as exc:
            messages.error(request, f'Документ не удалён из датасета: {exc}')

    return redirect('upload_documents')
