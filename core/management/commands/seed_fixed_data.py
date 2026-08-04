from django.core.management.base import BaseCommand
from core.models import NamHoc, Khoi, MonHoc, LopHoc, GiaoVien
from question_bank.models import MachKienThuc, NoiDungKienThuc
from django.contrib.auth.models import User
from datetime import date

class Command(BaseCommand):
    help = 'Tạo dữ liệu cứng cho các danh mục (Năm học, Khối, Lớp, Môn học, Giáo viên)'

    def handle(self, *args, **kwargs):
        self.stdout.write('Đang khởi tạo dữ liệu cứng...')

        # 1. Năm học
        nh, created = NamHoc.objects.get_or_create(
            TenNamHoc='2025-2026',
            defaults={
                'NgayBatDau': date(2025, 9, 5),
                'NgayKetThuc': date(2026, 5, 31)
            }
        )

        # 2. Khối
        khoi4, _ = Khoi.objects.get_or_create(TenKhoi='Khối 4')
        khoi5, _ = Khoi.objects.get_or_create(TenKhoi='Khối 5')

        # 3. Lớp học
        LopHoc.objects.get_or_create(MaNamHoc=nh, MaKhoi=khoi4, TenLop='4A')
        LopHoc.objects.get_or_create(MaNamHoc=nh, MaKhoi=khoi4, TenLop='4B')
        LopHoc.objects.get_or_create(MaNamHoc=nh, MaKhoi=khoi5, TenLop='5A')
        LopHoc.objects.get_or_create(MaNamHoc=nh, MaKhoi=khoi5, TenLop='5B')

        # 4. Môn học
        mon_toan, _ = MonHoc.objects.get_or_create(TenMon='Toán')
        mon_toan.KhoiApDung.add(khoi4, khoi5)

        mon_tv, _ = MonHoc.objects.get_or_create(TenMon='Tiếng Việt')
        mon_tv.KhoiApDung.add(khoi4, khoi5)
        
        mon_kh, _ = MonHoc.objects.get_or_create(TenMon='Khoa học')
        mon_kh.KhoiApDung.add(khoi4, khoi5)
        
        mon_lsdl, _ = MonHoc.objects.get_or_create(TenMon='Lịch sử & Địa lý')
        mon_lsdl.KhoiApDung.add(khoi4, khoi5)

        # 5. Mạch kiến thức (Toán)
        mach_so4, _ = MachKienThuc.objects.get_or_create(MonHoc=mon_toan, Khoi=khoi4, TenMach='Số và Phép tính')
        mach_hinh4, _ = MachKienThuc.objects.get_or_create(MonHoc=mon_toan, Khoi=khoi4, TenMach='Hình học và Đo lường')
        mach_thongke4, _ = MachKienThuc.objects.get_or_create(MonHoc=mon_toan, Khoi=khoi4, TenMach='Một số yếu tố Thống kê và Xác suất')
        
        mach_so5, _ = MachKienThuc.objects.get_or_create(MonHoc=mon_toan, Khoi=khoi5, TenMach='Số và Phép tính')
        mach_hinh5, _ = MachKienThuc.objects.get_or_create(MonHoc=mon_toan, Khoi=khoi5, TenMach='Hình học và Đo lường')
        mach_thongke5, _ = MachKienThuc.objects.get_or_create(MonHoc=mon_toan, Khoi=khoi5, TenMach='Một số yếu tố Thống kê và Xác suất')

        # Nội dung kiến thức (Toán)
        NoiDungKienThuc.objects.get_or_create(MachKienThuc=mach_so4, TenNoidung='Phân số và các phép tính với phân số')
        NoiDungKienThuc.objects.get_or_create(MachKienThuc=mach_so4, TenNoidung='Số tự nhiên và các phép tính với số tự nhiên')
        NoiDungKienThuc.objects.get_or_create(MachKienThuc=mach_hinh4, TenNoidung='Góc, đường thẳng song song, vuông góc')
        NoiDungKienThuc.objects.get_or_create(MachKienThuc=mach_hinh4, TenNoidung='Diện tích hình thoi, hình bình hành')
        
        NoiDungKienThuc.objects.get_or_create(MachKienThuc=mach_so5, TenNoidung='Số thập phân và các phép tính với số thập phân')
        NoiDungKienThuc.objects.get_or_create(MachKienThuc=mach_hinh5, TenNoidung='Hình hộp chữ nhật, hình lập phương')
        NoiDungKienThuc.objects.get_or_create(MachKienThuc=mach_hinh5, TenNoidung='Diện tích, thể tích các hình khối')

        # Mạch kiến thức (Tiếng Việt)
        mach_tv4, _ = MachKienThuc.objects.get_or_create(MonHoc=mon_tv, Khoi=khoi4, TenMach='Đọc hiểu')
        mach_tv4_ltdc, _ = MachKienThuc.objects.get_or_create(MonHoc=mon_tv, Khoi=khoi4, TenMach='Luyện từ và câu')
        mach_tv4_tlv, _ = MachKienThuc.objects.get_or_create(MonHoc=mon_tv, Khoi=khoi4, TenMach='Tập làm văn')

        NoiDungKienThuc.objects.get_or_create(MachKienThuc=mach_tv4, TenNoidung='Đọc hiểu văn bản truyện, thơ')
        NoiDungKienThuc.objects.get_or_create(MachKienThuc=mach_tv4_ltdc, TenNoidung='Mở rộng vốn từ, dấu câu')
        NoiDungKienThuc.objects.get_or_create(MachKienThuc=mach_tv4_tlv, TenNoidung='Văn miêu tả, kể chuyện')

        # 6. User và Giáo viên
        def create_user(username, full_name, role):
            u, created = User.objects.get_or_create(username=username, defaults={'first_name': full_name})
            if created or not u.has_usable_password():
                u.set_password('123456') # Mật khẩu mặc định, sẽ bị ép đổi khi đăng nhập
                u.save()
            gv, _ = GiaoVien.objects.get_or_create(user=u, defaults={
                'HoTen': full_name,
                'SDT': username,
                'ChucVu': role,
                'TrangThai': 'Đang hoạt động'
            })
            return gv

        bgh = create_user('0901234567', 'Thầy Hiệu Trưởng', 'Hiệu trưởng')
        tcm_toan = create_user('0901234568', 'Cô Tổ Trưởng Toán', 'Tổ trưởng chuyên môn')
        gv_toan = create_user('0901234569', 'Cô Giáo Toán', 'Giáo viên bộ môn')
        gv_tv = create_user('0901234570', 'Thầy Giáo Tiếng Việt', 'Giáo viên bộ môn')

        tcm_toan.MonGiangDay.add(mon_toan)
        tcm_toan.KhoiPhuTrach.add(khoi4, khoi5)
        
        gv_toan.MonGiangDay.add(mon_toan)
        gv_tv.MonGiangDay.add(mon_tv)

        self.stdout.write(self.style.SUCCESS('Tạo dữ liệu cứng thành công!'))
