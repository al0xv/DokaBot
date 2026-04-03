from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

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
