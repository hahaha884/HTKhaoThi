from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.cache import cache
from django.utils import timezone
from core.models import GiaoVien, Khoi, MonHoc

class LoginSecurityAndFunctionalTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        
        # Người dùng bình thường (đã từng đăng nhập)
        self.user = User.objects.create_user(username='0901234567', password='CorrectPassword123')
        self.user.last_login = timezone.now()
        self.user.save()
        self.giaovien = GiaoVien.objects.create(
            user=self.user,
            HoTen='Nguyễn Văn Test',
            SDT='0901234567',
            Email='gvtest@dangvanngu.edu.vn',
            ChucVu='Giáo viên bộ môn',
            TrangThai='Đang làm việc'
        )

        # Người dùng mới (đăng nhập lần đầu: last_login is None)
        self.new_user = User.objects.create_user(username='0987654321', password='DefaultPassword123')
        self.new_user.last_login = None
        self.new_user.save()
        self.new_giaovien = GiaoVien.objects.create(
            user=self.new_user,
            HoTen='Trần Thị Mới',
            SDT='0987654321',
            Email='gvmoi@dangvanngu.edu.vn',
            ChucVu='Giáo viên bộ môn',
            TrangThai='Đang làm việc'
        )

    def tearDown(self):
        cache.clear()

    # --- KỊCH BẢN CHÍNH (HAPPY PATHS) ---
    def test_login_page_renders_successfully(self):
        """Kịch bản chính: Màn hình đăng nhập hiển thị thành công (HTTP 200)."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/login.html')

    def test_login_success_regular_user(self):
        """Kịch bản chính: Đăng nhập thành công với tài khoản đã từng đăng nhập, điều hướng về trang chủ."""
        response = self.client.post(reverse('login'), {
            'sdt': '0901234567',
            'password': 'CorrectPassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/')
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_login_first_time_forces_password_change(self):
        """Kịch bản chính: Đăng nhập lần đầu (last_login is None) bắt buộc chuyển sang trang đổi mật khẩu."""
        response = self.client.post(reverse('login'), {
            'sdt': '0987654321',
            'password': 'DefaultPassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('change_password_first_login'))
        self.assertTrue(self.client.session.get('force_password_change'))

    def test_first_login_change_password_success(self):
        """Kịch bản chính: Đổi mật khẩu lần đầu thành công, xóa cờ ép đổi và vào trang chủ."""
        # Đăng nhập lần đầu
        self.client.post(reverse('login'), {
            'sdt': '0987654321',
            'password': 'DefaultPassword123'
        })
        # Gửi thông tin đổi mật khẩu hợp lệ
        response = self.client.post(reverse('change_password_first_login'), {
            'old_password': 'DefaultPassword123',
            'new_password': 'NewSecurePassword456',
            'confirm_password': 'NewSecurePassword456'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/')
        # Kiểm tra mật khẩu mới đã có hiệu lực
        self.new_user.refresh_from_db()
        self.assertTrue(self.new_user.check_password('NewSecurePassword456'))

    def test_logout_success(self):
        """Kịch bản chính: Đăng xuất phiên làm việc thành công, hủy session và về trang login."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    # --- KỊCH BẢN NGOẠI LỆ (EXCEPTION PATHS) ---
    def test_login_missing_credentials(self):
        """Ngoại lệ: Để trống số điện thoại hoặc mật khẩu."""
        response = self.client.post(reverse('login'), {
            'sdt': '',
            'password': ''
        })
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('đầy đủ số điện thoại và mật khẩu' in m.message for m in messages))

    def test_login_invalid_credentials(self):
        """Ngoại lệ: Nhập sai thông tin đăng nhập (mật khẩu hoặc tài khoản sai)."""
        response = self.client.post(reverse('login'), {
            'sdt': '0901234567',
            'password': 'WrongPassword999'
        })
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('không hợp lệ' in m.message for m in messages))
        # Số lần đăng nhập sai được ghi nhận trong cache
        self.assertEqual(cache.get('attempts_0901234567'), 1)

    def test_account_lockout_after_5_failed_attempts(self):
        """Ngoại lệ bảo mật: Khóa tài khoản tạm thời 5 phút sau 5 lần nhập sai liên tiếp."""
        for i in range(4):
            self.client.post(reverse('login'), {'sdt': '0901234567', 'password': 'Wrong'})
            self.assertFalse(cache.get('lockout_0901234567'))

        # Lần thứ 5
        response = self.client.post(reverse('login'), {'sdt': '0901234567', 'password': 'Wrong'})
        self.assertTrue(cache.get('lockout_0901234567'))
        messages = list(response.context['messages'])
        self.assertTrue(any('tạm khóa trong 5 phút do đăng nhập sai quá 05 lần' in m.message for m in messages))

    def test_login_blocked_while_account_locked(self):
        """Ngoại lệ bảo mật: Ngay cả khi nhập đúng mật khẩu trong lúc tài khoản bị khóa, hệ thống vẫn từ chối."""
        cache.set('lockout_0901234567', True, 300)
        response = self.client.post(reverse('login'), {
            'sdt': '0901234567',
            'password': 'CorrectPassword123'
        })
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('tạm khóa' in m.message for m in messages))

    def test_change_password_mismatched_confirmation(self):
        """Ngoại lệ: Mật khẩu xác nhận không khớp trong lần đăng nhập đầu tiên."""
        self.client.post(reverse('login'), {'sdt': '0987654321', 'password': 'DefaultPassword123'})
        response = self.client.post(reverse('change_password_first_login'), {
            'old_password': 'DefaultPassword123',
            'new_password': 'NewPassword123',
            'confirm_password': 'DifferentPassword123'
        })
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('không khớp' in m.message for m in messages))

    def test_change_password_wrong_old_password(self):
        """Ngoại lệ: Nhập sai mật khẩu cũ trong lần đăng nhập đầu tiên."""
        self.client.post(reverse('login'), {'sdt': '0987654321', 'password': 'DefaultPassword123'})
        response = self.client.post(reverse('change_password_first_login'), {
            'old_password': 'IncorrectOldPassword',
            'new_password': 'NewPassword123',
            'confirm_password': 'NewPassword123'
        })
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('hiện tại không đúng' in m.message for m in messages))
