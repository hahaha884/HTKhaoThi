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

        # Cập nhật hạn nộp
        res1 = self.client.post(reverse('matrix_set_deadline', args=[self.matran.pk]), {
            'deadline_type': 'nop',
            'deadline_date': new_dl.isoformat()
        })
        self.assertEqual(res1.status_code, 302)
        self.matran.refresh_from_db()
        self.assertEqual(self.matran.DeadlineNopDe, new_dl)

        # Cập nhật hạn sửa
        new_sua = date.today() + timedelta(days=5)
        res2 = self.client.post(reverse('matrix_set_deadline', args=[self.matran.pk]), {
            'deadline_type': 'sua',
            'deadline_date': new_sua.isoformat()
        })
        self.assertEqual(res2.status_code, 302)
        self.matran.refresh_from_db()
        self.assertEqual(self.matran.DeadlineSuaDe, new_sua)

    def test_tcm_set_deadline_for_giaovien(self):
        """TCM khi nhận ma trận đã duyệt thì set deadline làm đề cho giáo viên."""
        # Chuyển ma trận sang Đã duyệt
        self.matran.TrangThai = 'Đã duyệt'
        self.matran.save()

        self.client.login(username='totruong', password='password123')
        dl_gv = date.today() + timedelta(days=4)

        response = self.client.post(reverse('matrix_set_deadline_gv', args=[self.matran.pk]), {
            'gv_id': self.gv_bm.pk,
            'deadline_date': dl_gv.isoformat(),
            'ghi_chu': 'Thầy D làm đề 1 bám sát ma trận'
        })
        self.assertEqual(response.status_code, 302)

        gv_deadline = DeadlineGiaoVien.objects.filter(MaTran=self.matran, GiaoVien=self.gv_bm).first()
        self.assertIsNotNone(gv_deadline)
        self.assertEqual(gv_deadline.Deadline, dl_gv)
        self.assertEqual(gv_deadline.NguoiSet, self.gv_tcm)

    def test_deadline_status_logic(self):
        """Kiểm tra logic trễ hạn < 2 ngày ('urgent') hoặc hết hạn ('expired')."""
        today = date.today()

        # 1. Quá hạn (< 0 ngày) -> 'expired'
        dl_expired = DeadlineGiaoVien(
            MaTran=self.matran, GiaoVien=self.gv_bm, NguoiSet=self.gv_tcm,
            Deadline=today - timedelta(days=1)
        )
        self.assertEqual(dl_expired.deadline_status, 'expired')

        # 2. Hạn hôm nay (0 ngày) -> 'urgent' (< 2 ngày)
        dl_today = DeadlineGiaoVien(
            MaTran=self.matran, GiaoVien=self.gv_bm, NguoiSet=self.gv_tcm,
            Deadline=today
        )
        self.assertEqual(dl_today.deadline_status, 'urgent')

        # 3. Còn 1 ngày (1 ngày) -> 'urgent' (< 2 ngày)
        dl_tomorrow = DeadlineGiaoVien(
            MaTran=self.matran, GiaoVien=self.gv_bm, NguoiSet=self.gv_tcm,
            Deadline=today + timedelta(days=1)
        )
        self.assertEqual(dl_tomorrow.deadline_status, 'urgent')

        # 4. Còn >= 2 ngày -> 'ok'
        dl_safe = DeadlineGiaoVien(
            MaTran=self.matran, GiaoVien=self.gv_bm, NguoiSet=self.gv_tcm,
            Deadline=today + timedelta(days=2)
        )
        self.assertEqual(dl_safe.deadline_status, 'ok')

    def test_tcm_delete_deadline_gv(self):
        """TCM có thể xóa phân công deadline của giáo viên."""
        self.matran.TrangThai = 'Đã duyệt'
        self.matran.save()

        dl_record = DeadlineGiaoVien.objects.create(
            MaTran=self.matran,
            GiaoVien=self.gv_bm,
            NguoiSet=self.gv_tcm,
            Deadline=date.today() + timedelta(days=5)
        )

        self.client.login(username='totruong', password='password123')
        res = self.client.post(reverse('matrix_delete_deadline_gv', args=[self.matran.pk, dl_record.pk]))
        self.assertEqual(res.status_code, 302)
        self.assertFalse(DeadlineGiaoVien.objects.filter(pk=dl_record.pk).exists())

