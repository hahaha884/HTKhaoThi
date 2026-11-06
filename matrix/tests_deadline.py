from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import NamHoc, Khoi, MonHoc, GiaoVien
from matrix.models import MaTran, DeadlineGiaoVien

class MatrixDeadlineTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. BGH (Hiệu trưởng)
        self.user_bgh = User.objects.create_user(username='hieutruong', password='password123')
        self.gv_bgh = GiaoVien.objects.create(
            user=self.user_bgh,
            HoTen='Hiệu trưởng Nguyễn Văn B',
            ChucVu='Hiệu trưởng',
            SDT='0902000001'
        )

        # 2. TCM (Tổ trưởng)
        self.user_tcm = User.objects.create_user(username='totruong', password='password123')
        self.gv_tcm = GiaoVien.objects.create(
            user=self.user_tcm,
            HoTen='Tổ trưởng Trần Thị C',
            ChucVu='Tổ trưởng chuyên môn',
            SDT='0902000002'
        )

        # 3. GV (Giáo viên bộ môn)
        self.user_gv = User.objects.create_user(username='giaovien1', password='password123')
        self.gv_bm = GiaoVien.objects.create(
            user=self.user_gv,
            HoTen='Giáo viên Lê Văn D',
            ChucVu='Giáo viên bộ môn',
            SDT='0902000003'
        )

        self.namhoc, _ = NamHoc.objects.get_or_create(
            TenNamHoc='2026-2027',
            defaults={'NgayBatDau': date(2026, 9, 5), 'NgayKetThuc': date(2027, 5, 30)}
        )
        self.khoi = Khoi.objects.create(TenKhoi='Khối 4')
        self.monhoc = MonHoc.objects.create(TenMon='Tiếng Việt 4')

        # Tạo ma trận ở trạng thái Chờ duyệt
        self.matran = MaTran.objects.create(
            NguoiTao=self.gv_tcm,
            TenMaTran='Ma trận Tiếng Việt 4 Giữa kỳ 1',
            NamHoc=self.namhoc,
            HocKy='Học kỳ 1',
            KyThi='Giữa kỳ',
            MonHoc=self.monhoc,
            Khoi=self.khoi,
            TongSoCau=10,
            TongSoDiem=10,
            TrangThai='Chờ duyệt'
        )

    def test_bgh_approve_matrix_with_deadline_nop_de(self):
        """BGH duyệt ma trận thì cho nhập deadline nộp đề thi cho TCM."""
        self.client.login(username='hieutruong', password='password123')
        deadline_date = date.today() + timedelta(days=7)

        response = self.client.post(reverse('matrix_approve', args=[self.matran.pk]), {
            'action': 'approve',
            'DeadlineNopDe': deadline_date.isoformat(),
            'GhiChu': 'Duyệt ma trận, đề nghị TCM nộp đúng hạn'
        })
        self.assertEqual(response.status_code, 302)

        self.matran.refresh_from_db()
        self.assertEqual(self.matran.TrangThai, 'Đã duyệt')
        self.assertEqual(self.matran.DeadlineNopDe, deadline_date)
        self.assertEqual(self.matran.NguoiSetDeadline, self.gv_bgh)

    def test_bgh_reject_matrix_with_deadline_sua_de(self):
        """Khi làm sai mà sửa thì BGH cho deadline sửa."""
        self.client.login(username='hieutruong', password='password123')
        deadline_sua = date.today() + timedelta(days=3)

        response = self.client.post(reverse('matrix_approve', args=[self.matran.pk]), {
            'action': 'reject',
            'DeadlineSuaDe': deadline_sua.isoformat(),
            'GhiChu': 'Số câu mức 1 chưa đủ, yêu cầu điều chỉnh lại gấp'
        })
        self.assertEqual(response.status_code, 302)

        self.matran.refresh_from_db()
        self.assertEqual(self.matran.TrangThai, 'Từ chối')
        self.assertEqual(self.matran.DeadlineSuaDe, deadline_sua)
        self.assertEqual(self.matran.NguoiSetDeadline, self.gv_bgh)

    def test_bgh_set_deadline_independently(self):
        """BGH có thể cập nhật hạn nộp đề hoặc hạn sửa đề qua matrix_set_deadline."""
        self.client.login(username='hieutruong', password='password123')
        new_dl = date.today() + timedelta(days=10)

        # Cập nhật hạn nộp cho TCM
        res1 = self.client.post(reverse('matrix_set_deadline', args=[self.matran.pk]), {
            'deadline_type': 'nop',
            'deadline_date': new_dl.isoformat()
        })
        self.assertEqual(res1.status_code, 302)
        self.matran.refresh_from_db()
        self.assertEqual(self.matran.DeadlineNopDe, new_dl)

        # Cập nhật hạn sửa cho TCM
        new_sua = date.today() + timedelta(days=5)
        res2 = self.client.post(reverse('matrix_set_deadline', args=[self.matran.pk]), {
            'deadline_type': 'sua',
            'deadline_date': new_sua.isoformat()
        })
        self.assertEqual(res2.status_code, 302)
        self.matran.refresh_from_db()
        self.assertEqual(self.matran.DeadlineSuaDe, new_sua)

    def test_bgh_cannot_set_past_deadline(self):
        """Logic kiểm tra: Không cho phép đặt deadline trong quá khứ."""
        self.client.login(username='hieutruong', password='password123')
        past_date = date.today() - timedelta(days=1)

        # Thử duyệt với ngày quá khứ
        res = self.client.post(reverse('matrix_approve', args=[self.matran.pk]), {
            'action': 'approve',
            'DeadlineNopDe': past_date.isoformat()
        })
        self.matran.refresh_from_db()
        # Ma trận không bị đổi sang Đã duyệt nếu ngày nộp không hợp lệ
        self.assertNotEqual(self.matran.DeadlineNopDe, past_date)

    def test_deadline_status_and_days_remaining(self):
        """Kiểm tra logic tính toán deadline_status và days_remaining."""
        today = date.today()

        # 1. Hết hạn (quá hạn)
        self.matran.DeadlineNopDe = today - timedelta(days=2)
        self.assertEqual(self.matran.deadline_status, 'expired')
        self.assertEqual(self.matran.days_remaining, -2)

        # 2. Cận hạn (còn 1 ngày)
        self.matran.DeadlineNopDe = today + timedelta(days=1)
        self.assertEqual(self.matran.deadline_status, 'urgent')
        self.assertEqual(self.matran.days_remaining, 1)

        # 3. Còn hạn (còn 5 ngày)
        self.matran.DeadlineNopDe = today + timedelta(days=5)
        self.assertEqual(self.matran.deadline_status, 'ok')
        self.assertEqual(self.matran.days_remaining, 5)

    def test_detail_view_shows_bgh_deadline_and_tcm_assignment_modal(self):
        """Màn hình chi tiết ma trận hiển thị hạn BGH và nút/modal giao deadline nhân sự cho TCM."""
        self.matran.TrangThai = 'Đã duyệt'
        self.matran.DeadlineNopDe = date.today() + timedelta(days=5)
        self.matran.save()

        # Đăng nhập bằng tài khoản TCM
        self.client.login(username='totruong', password='password123')
        response = self.client.get(reverse('matrix_detail', args=[self.matran.pk]))
        self.assertEqual(response.status_code, 200)

        # Có hiển thị hạn nộp đề thi cho TCM
        self.assertContains(response, 'Hạn nộp đề thi (Tổ chuyên môn)')
        # Có hiển thị modal và nút giao deadline cho nhân sự
        self.assertContains(response, 'assignAllGvDeadlineModal')
        self.assertContains(response, 'Phân công Deadline làm đề cho Nhân sự')

    def test_tcm_set_deadline_for_all_teachers_at_once(self):
        """TCM chọn tất cả nhân sự 1 lần và set deadline 1 lần duy nhất."""
        self.matran.TrangThai = 'Đã duyệt'
        self.matran.DeadlineNopDe = date.today() + timedelta(days=7)
        self.matran.save()

        # Thêm thêm 1 giáo viên nữa
        user_gv2 = User.objects.create_user(username='giaovien2', password='password123')
        gv_bm2 = GiaoVien.objects.create(
            user=user_gv2,
            HoTen='Giáo viên Hoàng Thị E',
            ChucVu='Giáo viên chủ nhiệm',
            SDT='0902000004'
        )

        self.client.login(username='totruong', password='password123')
        dl_date = date.today() + timedelta(days=4)

        # Gửi request với select_all='1'
        response = self.client.post(reverse('matrix_set_deadline_gv', args=[self.matran.pk]), {
            'select_all': '1',
            'deadline_date': dl_date.isoformat(),
            'ghi_chu': 'Tất cả giáo viên trong tổ nộp 2 đề trước ngày quy định'
        })
        self.assertEqual(response.status_code, 302)

        # Cả 2 giáo viên (gv_bm và gv_bm2) đều có deadline
        dls = DeadlineGiaoVien.objects.filter(MaTran=self.matran)
        self.assertEqual(dls.count(), 3) # gv_tcm, gv_bm, gv_bm2
        for dl in dls:
            self.assertEqual(dl.Deadline, dl_date)
            self.assertEqual(dl.NguoiSet, self.gv_tcm)

    def test_tcm_set_deadline_for_multiple_selected_teachers(self):
        """TCM chọn danh sách nhiều giáo viên và set deadline cùng 1 lúc."""
        self.matran.TrangThai = 'Đã duyệt'
        self.matran.save()

        self.client.login(username='totruong', password='password123')
        dl_date = date.today() + timedelta(days=5)

        response = self.client.post(reverse('matrix_set_deadline_gv', args=[self.matran.pk]), {
            'gv_ids': [self.gv_bm.id],
            'deadline_date': dl_date.isoformat(),
            'ghi_chu': 'Phân công riêng'
        })
        self.assertEqual(response.status_code, 302)

        dl = DeadlineGiaoVien.objects.filter(MaTran=self.matran, GiaoVien=self.gv_bm).first()
        self.assertIsNotNone(dl)
        self.assertEqual(dl.Deadline, dl_date)
        self.assertEqual(dl.GhiChu, 'Phân công riêng')
