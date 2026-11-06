import json
import os
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import Khoi, MonHoc, GiaoVien

User = get_user_model()

class ImportWordPreviewTests(TestCase):
    def setUp(self):
        # Create a superuser for auth
        self.user = User.objects.create_superuser(username='admin', email='admin@example.com', password='adminpass')
        self.client = Client()
        self.client.login(username='admin', password='adminpass')
        # Create sample Khoi and MonHoc
        self.khoi = Khoi.objects.create(TenKhoi='Khối 1')
        self.mon = MonHoc.objects.create(TenMon='Toán')
        self.mon.KhoiApDung.add(self.khoi)
        # Simple docx file content (binary) – could be empty as we only test validation before processing
        self.dummy_file = b''

    def test_missing_khoi_or_mon_shows_error(self):
        url = reverse('import_word_preview')
        # Prepare POST without khoi_id and mon_id
        response = self.client.post(url, {'word_file': self.dummy_file}, follow=True)
        # The view should render the template with an error message
        self.assertContains(response, 'Vui lòng chọn Khối và Môn học trước khi tải lên đề thi.')

    def test_invalid_groq_key_shows_error(self):
        # Set a valid khoi_id and mon_id but ensure GROQ_API_KEY is missing
        from django.conf import settings
        if hasattr(settings, 'GROQ_API_KEY'):
            delattr(settings, 'GROQ_API_KEY')
        url = reverse('import_word_preview')
        data = {
            'khoi_id': str(self.khoi.id),
            'mon_id': str(self.mon.id),
            'word_file': self.dummy_file,
        }
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Cần cấu hình GROQ_API_KEY trong settings để sử dụng tính năng trích xuất thông minh.')

