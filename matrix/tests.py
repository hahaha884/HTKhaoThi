from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from core.models import NamHoc, Khoi, MonHoc, GiaoVien
from question_bank.models import MachKienThuc, NoiDungKienThuc
from matrix.models import MaTran, CT_MaTran
from matrix.services import validate_matrix_data, generate_matrix_docx


class MatrixBusinessRulesTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='totruong', password='password123')
        self.giaovien = GiaoVien.objects.create(
            user=self.user,
            HoTen='Nguyễn Văn A',
            ChucVu='Tổ trưởng chuyên môn',
            Email='totruong@dangvanngu.edu.vn',
            SDT='0901000001'
        )
        self.namhoc, _ = NamHoc.objects.get_or_create(
            TenNamHoc='2026-2027',
            defaults={
                'NgayBatDau': date(2026, 9, 5),
                'NgayKetThuc': date(2027, 5, 30)
            }
        )
        self.khoi = Khoi.objects.create(TenKhoi='Khối 5')
        self.monhoc = MonHoc.objects.create(TenMon='Toán')
        self.mach1 = MachKienThuc.objects.create(MonHoc=self.monhoc, Khoi=self.khoi, TenMach='Số học')
        self.noidung1 = NoiDungKienThuc.objects.create(MachKienThuc=self.mach1, TenNoidung='Phân số')
        self.noidung2 = NoiDungKienThuc.objects.create(MachKienThuc=self.mach1, TenNoidung='Số thập phân')

    def test_9a_missing_header_info(self):
        """Rule 9a: Thiếu thông tin bắt buộc"""
        header = {
            'TenMaTran': '',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk
        }
        res = validate_matrix_data(header, [], action='submit')
        self.assertFalse(res['is_valid'])
        self.assertTrue(any('thông tin bắt buộc' in e for e in res['errors']))

    def test_9b_duplicate_matrix(self):
        """Rule 9b: Ma trận đã tồn tại"""
        MaTran.objects.create(
            NguoiTao=self.giaovien,
            TenMaTran='Ma trận Toán 5 GK1',
            NamHoc=self.namhoc,
            HocKy='Học kỳ 1',
            KyThi='Giữa kỳ',
            Khoi=self.khoi,
            MonHoc=self.monhoc,
            TongSoCau=1,
            TongSoDiem=10.0,
            TrangThai='Nháp'
        )

        header = {
            'TenMaTran': 'Ma trận mới',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk
        }
        res = validate_matrix_data(header, [], action='submit')
        self.assertFalse(res['is_valid'])
        self.assertTrue(any('Ma trận đã tồn tại' in e for e in res['errors']))

    def test_9c_invalid_detail_values(self):
        """Rule 9c: Chi tiết ma trận không hợp lệ (Số câu <= 0 hoặc điểm <= 0)"""
        header = {
            'TenMaTran': 'Ma trận Toán 5',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk
        }
        details = [{
            'MachKienThuc': self.mach1.pk,
            'NoiDung': self.noidung1.pk,
            'MucDo': 'Mức 1',
            'LoaiCauHoi': 'Trắc nghiệm',
            'SoLuongCau': 0,
            'CauSo': '1',
            'Diem': 0,
            'TyLe': 100
        }]
        res = validate_matrix_data(header, details, action='submit')
        self.assertFalse(res['is_valid'])
        self.assertIn(0, res['row_errors'])

    def test_9d_invalid_total_points(self):
        """Rule 9d: Tổng điểm khác 10 không hợp lệ"""
        header = {
            'TenMaTran': 'Ma trận Toán 5',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk
        }
        details = [{
            'MachKienThuc': self.mach1.pk,
            'NoiDung': self.noidung1.pk,
            'MucDo': 'Mức 1',
            'LoaiCauHoi': 'Trắc nghiệm',
            'SoLuongCau': 1,
            'CauSo': '1',
            'Diem': 8.0,
            'TyLe': 100.0
        }]
        res = validate_matrix_data(header, details, action='submit')
        self.assertFalse(res['is_valid'])
        self.assertTrue(any('Tổng điểm của ma trận phải bằng 10 điểm' in e for e in res['errors']))

    def test_9e_duplicate_detail_combination(self):
        """Rule 9e: Trùng dòng chi tiết ma trận (Mạch + Nội dung + Mức độ + Loại)"""
        header = {
            'TenMaTran': 'Ma trận Toán 5',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk
        }
        details = [
            {
                'MachKienThuc': self.mach1.pk,
                'NoiDung': self.noidung1.pk,
                'MucDo': 'Mức 1',
                'LoaiCauHoi': 'Trắc nghiệm',
                'SoLuongCau': 1,
                'CauSo': '1',
                'Diem': 5.0,
                'TyLe': 50.0
            },
            {
                'MachKienThuc': self.mach1.pk,
                'NoiDung': self.noidung1.pk,
                'MucDo': 'Mức 1',
                'LoaiCauHoi': 'Trắc nghiệm',
                'SoLuongCau': 1,
                'CauSo': '2',
                'Diem': 5.0,
                'TyLe': 50.0
            }
        ]
        res = validate_matrix_data(header, details, action='submit')
        self.assertFalse(res['is_valid'])
        self.assertIn(1, res['row_errors'])
        self.assertTrue(any('trùng tổ hợp' in err for err in res['row_errors'][1]))

    def test_9f_duplicate_question_number(self):
        """Rule 9f: Câu số bị trùng trong ma trận"""
        header = {
            'TenMaTran': 'Ma trận Toán 5',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk
        }
        details = [
            {
                'MachKienThuc': self.mach1.pk,
                'NoiDung': self.noidung1.pk,
                'MucDo': 'Mức 1',
                'LoaiCauHoi': 'Trắc nghiệm',
                'SoLuongCau': 1,
                'CauSo': '1',
                'Diem': 5.0,
                'TyLe': 50.0
            },
            {
                'MachKienThuc': self.mach1.pk,
                'NoiDung': self.noidung2.pk,
                'MucDo': 'Mức 2',
                'LoaiCauHoi': 'Trắc nghiệm',
                'SoLuongCau': 1,
                'CauSo': '1',  # Trùng câu số 1
                'Diem': 5.0,
                'TyLe': 50.0
            }
        ]
        res = validate_matrix_data(header, details, action='submit')
        self.assertFalse(res['is_valid'])
        self.assertIn(1, res['row_errors'])
        self.assertTrue(any('đã tồn tại trong ma trận' in err for err in res['row_errors'][1]))

    def test_9g_invalid_total_percentage(self):
        """Rule 9g: Tổng tỷ lệ khác 100%"""
        header = {
            'TenMaTran': 'Ma trận Toán 5',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk
        }
        details = [{
            'MachKienThuc': self.mach1.pk,
            'NoiDung': self.noidung1.pk,
            'MucDo': 'Mức 1',
            'LoaiCauHoi': 'Trắc nghiệm',
            'SoLuongCau': 1,
            'CauSo': '1',
            'Diem': 10.0,
            'TyLe': 90.0  # 90% != 100%
        }]
        res = validate_matrix_data(header, details, action='submit')
        self.assertFalse(res['is_valid'])
        self.assertTrue(any('Tổng tỷ lệ của ma trận phải bằng 100%' in e for e in res['errors']))

    def test_9h_invalid_question_number_format(self):
        """Rule 9h: Câu số không hợp lệ (sai định dạng, ký tự, số âm, số 0)"""
        header = {
            'TenMaTran': 'Ma trận Toán 5',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk
        }
        for bad_causo in ['1,a,3', '1.5', '-1', '0', '1,,2', '1;2', '1-2', '1, ,3']:
            details = [{
                'MachKienThuc': self.mach1.pk,
                'NoiDung': self.noidung1.pk,
                'MucDo': 'Mức 1',
                'LoaiCauHoi': 'Trắc nghiệm',
                'SoLuongCau': 1,
                'CauSo': bad_causo,
                'Diem': 10.0,
                'TyLe': 100.0
            }]
            res = validate_matrix_data(header, details, action='submit')
            self.assertFalse(res['is_valid'], f"Expected failure for causo: {bad_causo}")
            self.assertIn(0, res['row_errors'])
            self.assertTrue(any('Câu số không hợp lệ' in err for err in res['row_errors'][0]))

    def test_9i_soluong_mismatch_causo(self):
        """Rule 9i: Số lượng câu không khớp Câu số"""
        header = {
            'TenMaTran': 'Ma trận Toán 5',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk
        }
        details = [{
            'MachKienThuc': self.mach1.pk,
            'NoiDung': self.noidung1.pk,
            'MucDo': 'Mức 1',
            'LoaiCauHoi': 'Trắc nghiệm',
            'SoLuongCau': 2,  # Khai báo 2 câu nhưng chỉ nhập 1 câu số
            'CauSo': '1',
            'Diem': 10.0,
            'TyLe': 100.0
        }]
        res = validate_matrix_data(header, details, action='submit')
        self.assertFalse(res['is_valid'])
        self.assertIn(0, res['row_errors'])
        self.assertTrue(any('phải bằng số lượng Câu số đã khai báo' in err for err in res['row_errors'][0]))

    def test_9j_invalid_percentage_range(self):
        """Rule 9j: Tỷ lệ <= 0 hoặc > 100"""
        header = {
            'TenMaTran': 'Ma trận Toán 5',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk
        }
        for bad_tyle in [0, -5, 105]:
            details = [{
                'MachKienThuc': self.mach1.pk,
                'NoiDung': self.noidung1.pk,
                'MucDo': 'Mức 1',
                'LoaiCauHoi': 'Trắc nghiệm',
                'SoLuongCau': 1,
                'CauSo': '1',
                'Diem': 10.0,
                'TyLe': bad_tyle
            }]
            res = validate_matrix_data(header, details, action='submit')
            self.assertFalse(res['is_valid'])
            self.assertIn(0, res['row_errors'])

    def test_9k_level_percentage_rounding_tens(self):
        """Rule 9k: Tỷ lệ % tính theo tổng điểm và làm tròn hàng chục (không đặt ngưỡng ±5%)"""
        header = {
            'TenMaTran': 'Ma trận Toán 5',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk
        }
        # Tổng điểm = 10.0đ:
        # C1 Mức 1: 3.1đ -> (3.1 / 10) * 100 = 31% -> làm tròn xuống 30%
        # C2 Mức 2: 6.9đ -> (6.9 / 10) * 100 = 69% -> làm tròn lên 70%
        details = [
            {
                'MachKienThuc': self.mach1.pk,
                'NoiDung': self.noidung1.pk,
                'MucDo': 'Mức 1',
                'LoaiCauHoi': 'Trắc nghiệm',
                'SoLuongCau': 1,
                'CauSo': '1',
                'Diem': 3.1,
                'TyLe': 30.0
            },
            {
                'MachKienThuc': self.mach1.pk,
                'NoiDung': self.noidung2.pk,
                'MucDo': 'Mức 2',
                'LoaiCauHoi': 'Trắc nghiệm',
                'SoLuongCau': 1,
                'CauSo': '2',
                'Diem': 6.9,
                'TyLe': 70.0
            }
        ]
        res = validate_matrix_data(header, details, action='submit')
        self.assertTrue(res['is_valid'])
        self.assertEqual(res['calc_summary']['tong_diem'], 10.0)
        self.assertEqual(res['calc_summary']['muc_do']['Mức 1']['tyle_lamtron'], 30)
        self.assertEqual(res['calc_summary']['muc_do']['Mức 2']['tyle_lamtron'], 70)

    def test_valid_matrix_submission(self):
        """Kiểm tra ma trận hoàn toàn hợp lệ"""
        header = {
            'TenMaTran': 'Ma trận Toán 5 GK1 Chuẩn',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk
        }
        # Mức 1: 4đ (40%), Mức 2: 3đ (30%), Mức 3: 3đ (30%) -> Tổng 10đ, 100%, Lệch 0%
        details = [
            {
                'MachKienThuc': self.mach1.pk,
                'NoiDung': self.noidung1.pk,
                'MucDo': 'Mức 1',
                'LoaiCauHoi': 'Trắc nghiệm',
                'SoLuongCau': 4,
                'CauSo': '1,2,3,4',
                'Diem': 4.0,
                'TyLe': 40.0
            },
            {
                'MachKienThuc': self.mach1.pk,
                'NoiDung': self.noidung2.pk,
                'MucDo': 'Mức 2',
                'LoaiCauHoi': 'Trắc nghiệm',
                'SoLuongCau': 3,
                'CauSo': '5,6,7',
                'Diem': 3.0,
                'TyLe': 30.0
            },
            {
                'MachKienThuc': self.mach1.pk,
                'NoiDung': self.noidung2.pk,
                'MucDo': 'Mức 3',
                'LoaiCauHoi': 'Tự luận',
                'SoLuongCau': 1,
                'CauSo': '8',
                'Diem': 3.0,
                'TyLe': 30.0
            }
        ]
        res = validate_matrix_data(header, details, action='submit')
        self.assertTrue(res['is_valid'])
        self.assertEqual(res['calc_summary']['tong_so_cau'], 8)
        self.assertEqual(res['calc_summary']['tong_diem'], 10.0)
        self.assertEqual(res['calc_summary']['tong_tyle'], 100.0)

    def test_uc_9_5_docx_generation(self):
        """UC 9.5: Sinh file Word (.docx) hợp lệ"""
        matran = MaTran.objects.create(
            NguoiTao=self.giaovien,
            TenMaTran='Ma trận Toán Khối 5',
            NamHoc=self.namhoc,
            HocKy='Học kỳ 1',
            KyThi='Giữa kỳ',
            Khoi=self.khoi,
            MonHoc=self.monhoc,
            TongSoCau=2,
            TongSoDiem=10.0,
            TrangThai='Đã duyệt'
        )
        CT_MaTran.objects.create(
            MaTran=matran,
            MachKienThuc=self.mach1,
            NoiDung=self.noidung1,
            MucDo='Mức 1',
            LoaiCauHoi='Trắc nghiệm',
            SoLuongCau=2,
            CauSo='1,2',
            Diem=10.0,
            TyLe=100.0
        )
        buf = generate_matrix_docx(matran)
        self.assertIsNotNone(buf)
        self.assertGreater(buf.getbuffer().nbytes, 1000)


class MatrixViewsIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_tcm = User.objects.create_user(username='totruong_view', password='password123')
        self.gv_tcm = GiaoVien.objects.create(
            user=self.user_tcm,
            HoTen='Trần Tổ Trưởng',
            ChucVu='Tổ trưởng chuyên môn',
            Email='totruong_view@dangvanngu.edu.vn',
            SDT='0902000001'
        )

        self.user_bgh = User.objects.create_user(username='hieutruong_view', password='password123')
        self.gv_bgh = GiaoVien.objects.create(
            user=self.user_bgh,
            HoTen='Lê Hiệu Trưởng',
            ChucVu='Hiệu trưởng',
            Email='hieutruong@dangvanngu.edu.vn',
            SDT='0902000002'
        )

        self.namhoc, _ = NamHoc.objects.get_or_create(
            TenNamHoc='2026-2027',
            defaults={
                'NgayBatDau': date(2026, 9, 5),
                'NgayKetThuc': date(2027, 5, 30)
            }
        )
        self.khoi = Khoi.objects.create(TenKhoi='Khối 4')
        self.monhoc = MonHoc.objects.create(TenMon='Tiếng Việt')
        self.mach = MachKienThuc.objects.create(MonHoc=self.monhoc, Khoi=self.khoi, TenMach='Đọc hiểu')
        self.noidung = NoiDungKienThuc.objects.create(MachKienThuc=self.mach, TenNoidung='Văn bản tự sự')

    def test_uc_9_1_create_and_submit(self):
        """UC 9.1: Tạo ma trận đề thi và nộp phê duyệt trực tiếp (Chờ duyệt)."""
        self.client.login(username='totruong_view', password='password123')

        # Nộp ma trận hoàn chỉnh (Chờ duyệt)
        post_submit = {
            'action': 'submit',
            'TenMaTran': 'Ma trận TV 4 Gửi Duyệt',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk,
            'MoTa': 'Đề xuất',
            'MachKienThuc[]': [str(self.mach.pk)],
            'NoiDung[]': [str(self.noidung.pk)],
            'MucDo[]': ['Mức 1'],
            'LoaiCauHoi[]': ['Trắc nghiệm'],
            'SoLuongCau[]': ['2'],
            'CauSo[]': ['1,2'],
            'Diem[]': ['10.0'],
            'TyLe[]': ['100.0'],
        }
        res_submit = self.client.post('/ma-tran/them/', post_submit)
        self.assertEqual(res_submit.status_code, 302)
        mt_submitted = MaTran.objects.get(TenMaTran='Ma trận TV 4 Gửi Duyệt')
        self.assertEqual(mt_submitted.TrangThai, 'Chờ duyệt')
        self.assertEqual(mt_submitted.TongSoCau, 2)
        self.assertEqual(mt_submitted.TongSoDiem, 10.0)

    def test_uc_9_2_update_matrix(self):
        self.client.login(username='totruong_view', password='password123')
        matran = MaTran.objects.create(
            NguoiTao=self.gv_tcm,
            TenMaTran='Ma trận cần sửa',
            NamHoc=self.namhoc,
            HocKy='Học kỳ 1',
            KyThi='Giữa kỳ',
            Khoi=self.khoi,
            MonHoc=self.monhoc,
            TongSoCau=1,
            TongSoDiem=10.0,
            TrangThai='Nháp'
        )
        post_update = {
            'action': 'submit',
            'TenMaTran': 'Ma trận đã sửa hoàn chỉnh',
            'NamHoc': self.namhoc.pk,
            'HocKy': 'Học kỳ 1',
            'KyThi': 'Giữa kỳ',
            'Khoi': self.khoi.pk,
            'MonHoc': self.monhoc.pk,
            'MoTa': 'Đã sửa',
            'MachKienThuc[]': [str(self.mach.pk)],
            'NoiDung[]': [str(self.noidung.pk)],
            'MucDo[]': ['Mức 1'],
            'LoaiCauHoi[]': ['Trắc nghiệm'],
            'SoLuongCau[]': ['1'],
            'CauSo[]': ['1'],
            'Diem[]': ['10.0'],
            'TyLe[]': ['100.0'],
        }
        res = self.client.post(f'/ma-tran/{matran.pk}/sua/', post_update)
        self.assertEqual(res.status_code, 302)
        matran.refresh_from_db()
        self.assertEqual(matran.TenMaTran, 'Ma trận đã sửa hoàn chỉnh')
        self.assertEqual(matran.TrangThai, 'Chờ duyệt')

    def test_uc_9_3_delete_matrix(self):
        self.client.login(username='totruong_view', password='password123')
        # Ma trận nháp -> được phép xóa
        mt_nhap = MaTran.objects.create(
            NguoiTao=self.gv_tcm,
            TenMaTran='Ma trận xóa nháp',
            NamHoc=self.namhoc,
            HocKy='Học kỳ 1',
            KyThi='Giữa kỳ',
            Khoi=self.khoi,
            MonHoc=self.monhoc,
            TongSoCau=1,
            TongSoDiem=10.0,
            TrangThai='Nháp'
        )
        res_del = self.client.post(f'/ma-tran/{mt_nhap.pk}/xoa/')
        self.assertEqual(res_del.status_code, 302)
        self.assertFalse(MaTran.objects.filter(pk=mt_nhap.pk).exists())

        # Ma trận đã duyệt -> không được phép xóa
        mt_duyet = MaTran.objects.create(
            NguoiTao=self.gv_tcm,
            TenMaTran='Ma trận đã duyệt không được xóa',
            NamHoc=self.namhoc,
            HocKy='Học kỳ 2',
            KyThi='Cuối kỳ',
            Khoi=self.khoi,
            MonHoc=self.monhoc,
            TongSoCau=1,
            TongSoDiem=10.0,
            TrangThai='Đã duyệt'
        )
        res_del_fail = self.client.post(f'/ma-tran/{mt_duyet.pk}/xoa/')
        self.assertEqual(res_del_fail.status_code, 302)
        self.assertTrue(MaTran.objects.filter(pk=mt_duyet.pk).exists())

    def test_uc_9_4_search_and_filter(self):
        self.client.login(username='totruong_view', password='password123')
        MaTran.objects.create(
            NguoiTao=self.gv_tcm,
            TenMaTran='Ma trận Đặc Biệt Alpha',
            NamHoc=self.namhoc,
            HocKy='Học kỳ 1',
            KyThi='Giữa kỳ',
            Khoi=self.khoi,
            MonHoc=self.monhoc,
            TongSoCau=1,
            TongSoDiem=10.0,
            TrangThai='Đã duyệt'
        )
        # Tìm theo từ khóa
        res = self.client.get('/ma-tran/?search=Alpha')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Ma trận Đặc Biệt Alpha')

        # Tìm từ khóa không tồn tại
        res_empty = self.client.get('/ma-tran/?search=XYZKHONGCO')
        self.assertEqual(res_empty.status_code, 200)
        self.assertContains(res_empty, 'Không tìm thấy ma trận phù hợp.')

    def test_uc_9_5_export_formats(self):
        self.client.login(username='totruong_view', password='password123')
        mt = MaTran.objects.create(
            NguoiTao=self.gv_tcm,
            TenMaTran='Ma trận Xuất Thử',
            NamHoc=self.namhoc,
            HocKy='Học kỳ 1',
            KyThi='Giữa kỳ',
            Khoi=self.khoi,
            MonHoc=self.monhoc,
            TongSoCau=1,
            TongSoDiem=10.0,
            TrangThai='Đã duyệt'
        )
        CT_MaTran.objects.create(
            MaTran=mt,
            MachKienThuc=self.mach,
            NoiDung=self.noidung,
            MucDo='Mức 1',
            LoaiCauHoi='Trắc nghiệm',
            SoLuongCau=1,
            CauSo='1',
            Diem=10.0,
            TyLe=100.0
        )
        # Xuất Word (.docx)
        res_docx = self.client.get(f'/ma-tran/{mt.pk}/xuat/?format=docx')
        self.assertEqual(res_docx.status_code, 200)
        self.assertEqual(res_docx['Content-Type'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')

        # Xuất Excel (.xls)
        res_xls = self.client.get(f'/ma-tran/{mt.pk}/xuat/?format=excel')
        self.assertEqual(res_xls.status_code, 200)
        self.assertIn('application/vnd.ms-excel', res_xls['Content-Type'])
