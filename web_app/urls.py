from django.contrib.auth import views as auth_views
from django.urls import path

from .views import delete_document_view, register_view, upload_documents_view

urlpatterns = [
    path('', upload_documents_view, name='upload_documents'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', register_view, name='register'),
    path('documents/<int:document_id>/delete/', delete_document_view, name='delete_document'),
]
