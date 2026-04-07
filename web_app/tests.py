from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from unittest.mock import patch

from .models import Document


class DocumentIsolationTests(TestCase):
    def setUp(self):
        self.school_1 = User.objects.create_user(username='school1', password='pass12345')
        self.school_2 = User.objects.create_user(username='school2', password='pass12345')
        self.client = Client()

    def test_school_sees_only_own_documents(self):
        Document.objects.create(
            school=self.school_1,
            title='Doc 1',
            file=SimpleUploadedFile('doc1.txt', b'content 1'),
        )
        Document.objects.create(
            school=self.school_2,
            title='Doc 2',
            file=SimpleUploadedFile('doc2.txt', b'content 2'),
        )

        self.client.login(username='school1', password='pass12345')
        response = self.client.get(reverse('upload_documents'))

        self.assertContains(response, 'Doc 1')
        self.assertNotContains(response, 'Doc 2')

    @patch('web_app.views.sync_document_to_vector_store', return_value='vs-file-1')
    def test_upload_saves_document_in_vector_store(self, sync_document_to_vector_store):
        self.client.login(username='school1', password='pass12345')

        response = self.client.post(
            reverse('upload_documents'),
            {
                'title': 'Rules',
                'file': SimpleUploadedFile('rules.txt', b'rules content'),
            },
            follow=True,
        )

        document = Document.objects.get(title='Rules')
        self.assertRedirects(response, reverse('upload_documents'))
        self.assertEqual(document.vector_store_file_id, 'vs-file-1')
        sync_document_to_vector_store.assert_called_once()

    @patch('web_app.views.remove_document_from_vector_store')
    def test_delete_removes_document_from_vector_store(self, remove_document_from_vector_store):
        self.client.login(username='school1', password='pass12345')
        document = Document.objects.create(
            school=self.school_1,
            title='Doc 1',
            file=SimpleUploadedFile('doc1.txt', b'content 1'),
            vector_store_file_id='vs-file-1',
        )

        response = self.client.post(reverse('delete_document', args=[document.id]), follow=True)

        self.assertRedirects(response, reverse('upload_documents'))
        self.assertFalse(Document.objects.filter(id=document.id).exists())
        remove_document_from_vector_store.assert_called_once()
