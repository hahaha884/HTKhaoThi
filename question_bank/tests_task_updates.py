from django.test import TestCase, Client
from django.contrib.auth.models import User
from core.models import GiaoVien, Khoi, MonHoc
from question_bank.models import CauHoi, DapAn, NhomCauHoi
from matrix.models import MaTran
from exam.models import DeThi, DeThi_CT

class TaskUpdatesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Tạo user & giáo viên
        self.bgh_user = User.objects.create_user(username='bgh_user', password='password123')
        self.bgh_gv = GiaoVien.objects.create(
            user=self.bgh_user,
            HoTen='Nguyễn Văn Hiệu Trưởng',
            ChucVu='Hiệu trưởng',
            SDT='0901234567'
        )
        
        self.gv_user = User.objects.create_user(username='gv_user', password='password123')
        self.gv = GiaoVien.objects.create(
            user=self.gv_user,
            HoTen='Trần Thị Giáo Viên',
            ChucVu='Giáo viên bộ môn',
            SDT='0907654321'
        )

        self.tcm_user = User.objects.create_user(username='tcm_user', password='password123')
        self.tcm_gv = GiaoVien.objects.create(
            user=self.tcm_user,
            HoTen='Lê Văn Tổ Trưởng',
            ChucVu='Tổ trưởng chuyên môn',
            SDT='0909999999'
        )

        self.khoi = Khoi.objects.create(TenKhoi='Khối 5')
        self.mon = MonHoc.objects.create(TenMon='Toán')
        self.mon.KhoiApDung.add(self.khoi)

    def test_bgh_cannot_create_matrix(self):
        """BGH không được quyền tạo ma trận đề thi"""
        from django.urls import reverse
        self.client.login(username='bgh_user', password='password123')
        response = self.client.get(reverse('matrix_create'))
        # Phải redirect về matrix_list
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('matrix_list'), response.url)

    def test_bgh_cannot_start_exam_wizard(self):
        """BGH không được tạo đề thi mới trực tiếp"""
        from django.urls import reverse
        self.client.login(username='bgh_user', password='password123')
        response = self.client.get(reverse('exam_wizard_start'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('exam_list'), response.url)

    def test_question_bank_filter_by_creator(self):
        """Lọc câu hỏi theo người tạo"""
        # Tạo 2 câu hỏi bởi 2 người khác nhau
        q1 = CauHoi.objects.create(
            Khoi=self.khoi, MonHoc=self.mon, NguoiTao=self.gv,
            DangCauHoi='MCQ', MucDo='Mức 1', NoiDungCauHoi='Câu hỏi 1'
        )
        q2 = CauHoi.objects.create(
            Khoi=self.khoi, MonHoc=self.mon, NguoiTao=self.tcm_gv,
            DangCauHoi='MCQ', MucDo='Mức 1', NoiDungCauHoi='Câu hỏi 2'
        )

        self.client.login(username='gv_user', password='password123')
        
        # Không lọc -> Thấy cả 2
        res_all = self.client.get('/cau-hoi/')
        self.assertEqual(res_all.status_code, 200)
        self.assertIn(q1, res_all.context['questions'])
        self.assertIn(q2, res_all.context['questions'])

        # Lọc theo GV 1 -> Chỉ thấy q1
        res_gv = self.client.get(f'/cau-hoi/?nguoi_tao={self.gv.id}')
        self.assertEqual(res_gv.status_code, 200)
        self.assertIn(q1, res_gv.context['questions'])
        self.assertNotIn(q2, res_gv.context['questions'])

    def test_matching_and_fib_creation(self):
        """Tạo câu hỏi Matching và FIB thành công"""
        # 1. Matching
        q_match = CauHoi.objects.create(
            Khoi=self.khoi, MonHoc=self.mon, NguoiTao=self.gv,
            DangCauHoi='Matching', MucDo='Mức 2', NoiDungCauHoi='Nối từ với nghĩa'
        )
        DapAn.objects.create(CauHoi=q_match, ThuTu=0, NoiDungTrai='Chó', NoiDung='Động vật 4 chân', LaDapAnDung=True)
        DapAn.objects.create(CauHoi=q_match, ThuTu=1, NoiDungTrai='Chim', NoiDung='Động vật có cánh', LaDapAnDung=True)
        self.assertEqual(q_match.dap_ans.count(), 2)

        # 2. FIB
        q_fib = CauHoi.objects.create(
            Khoi=self.khoi, MonHoc=self.mon, NguoiTao=self.gv,
            DangCauHoi='FIB', MucDo='Mức 1', NoiDungCauHoi='Hà Nội là [...] của Việt Nam.'
        )
        DapAn.objects.create(CauHoi=q_fib, ThuTu=0, NoiDung='thủ đô', LaDapAnDung=True)
        self.assertEqual(q_fib.dap_ans.count(), 1)
        self.assertEqual(q_fib.dap_ans.first().NoiDung, 'thủ đô')

    def test_bgh_clone_exam_and_mark_as_read(self):
        """BGH có thể tạo bản sao đề thi và đánh dấu Đã đọc vào DB"""
        from matrix.models import MaTran
        from core.models import NamHoc
        from django.urls import reverse

        from datetime import date
        nam_hoc = NamHoc.objects.first()
        if not nam_hoc:
            nam_hoc = NamHoc.objects.create(
                TenNamHoc='2025-2026',
                NgayBatDau=date(2025, 9, 5),
                NgayKetThuc=date(2026, 5, 31)
            )
        matran = MaTran.objects.create(
            TenMaTran='Ma trận chuẩn', NamHoc=nam_hoc, Khoi=self.khoi, MonHoc=self.mon,
            HocKy='Học kỳ 1', KyThi='Giữa kỳ', NguoiTao=self.tcm_gv, TrangThai='Đã duyệt'
        )
        de_goc = DeThi.objects.create(
            TenDe='Đề thi mẫu', MaMaTran=matran, NamHoc=nam_hoc, Khoi=self.khoi, MonHoc=self.mon,
            HocKy='Học kỳ 1', KyThi='Giữa kỳ', NguoiTao=self.gv, TrangThai='Đã nộp',
            NguoiDuyet=self.bgh_gv, TrangThaiDoc='Chưa đọc', TongDiem=10.0
        )

        self.client.login(username='bgh_user', password='password123')

        # 1. Thao tác 'Đã đọc'
        res_read = self.client.post(reverse('exam_editor', kwargs={'pk': de_goc.pk}), {'action': 'mark_as_read'})
        self.assertEqual(res_read.status_code, 302)
        de_goc.refresh_from_db()
        self.assertEqual(de_goc.TrangThaiDoc, 'Đã đọc')
        self.assertEqual(de_goc.NguoiDoc, self.bgh_gv)

        # 2. Thao tác 'clone_exam'
        res_clone = self.client.post(reverse('exam_editor', kwargs={'pk': de_goc.pk}), {'action': 'clone_exam'})
        self.assertEqual(res_clone.status_code, 302)
        # Đề gốc vẫn nguyên vẹn
        de_goc.refresh_from_db()
        self.assertEqual(de_goc.TrangThai, 'Đã nộp')

        # Bản sao mới được tạo
        clones = DeThi.objects.filter(DeGoc=de_goc)
        self.assertEqual(clones.count(), 1)
        clone = clones.first()
        self.assertNotEqual(clone.pk, de_goc.pk)
        self.assertEqual(clone.NguoiTao, self.bgh_gv)
        self.assertEqual(clone.TrangThai, 'Nháp')
        self.assertIn('Bản sao', clone.TenDe)
