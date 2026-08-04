"""
Tạo đầy đủ giáo viên chủ nhiệm + giáo viên bộ môn cho trường tiểu học 5 khối.

Theo chương trình GDPT 2018 cấp Tiểu học:
- GVCN (Khối 1-3): dạy Toán, Tiếng Việt, Đạo đức, Tự nhiên & Xã hội, HĐTN
- GVCN (Khối 4-5): dạy Toán, Tiếng Việt, Đạo đức, Khoa học, Lịch sử & Địa lý, HĐTN
- GV Tiếng Anh: dạy Tiếng Anh (Khối 1-5)
- GV Tin học: dạy Tin học (Khối 3-5)
- GV Âm nhạc: dạy Âm nhạc (Khối 1-5)
- GV Mỹ thuật: dạy Mỹ thuật (Khối 1-5)
- GV GDTC: dạy Giáo dục thể chất (Khối 1-5)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import GiaoVien, MonHoc, Khoi, LopHoc, NamHoc

def tao_giaovien(sdt, hoten, gioitinh, chuc_vu, ten_mon_list):
    """Tạo/cập nhật giáo viên và gán môn giảng dạy"""
    password = '123456'
    user, _ = User.objects.get_or_create(username=sdt)
    user.set_password(password)
    user.save()

    gv, created = GiaoVien.objects.get_or_create(SDT=sdt, defaults={
        'user': user, 'HoTen': hoten, 'GioiTinh': gioitinh,
        'ChucVu': chuc_vu, 'TrangThai': 'Đang hoạt động',
    })
    if not created:
        gv.user = user; gv.HoTen = hoten; gv.GioiTinh = gioitinh
        gv.ChucVu = chuc_vu; gv.TrangThai = 'Đang hoạt động'; gv.save()

    mon_hocs = MonHoc.objects.filter(TenMon__in=ten_mon_list)
    gv.MonGiangDay.set(mon_hocs)
    return gv

def gan_lop_chuyen_nhiem(gv, ten_lop):
    """Gán lớp chủ nhiệm cho GVCN"""
    nam = NamHoc.objects.order_by('-id').first()
    ten_khoi = 'Khối ' + ten_lop[0]
    khoi = Khoi.objects.filter(TenKhoi=ten_khoi).first()
    if nam and khoi:
        lop, _ = LopHoc.objects.get_or_create(
            TenLop=ten_lop, MaNamHoc=nam, MaKhoi=khoi,
            defaults={'GVCN': gv, 'SiSoToiDa': 35}
        )
        lop.GVCN = gv; lop.save()

# ===== MÔN HỌC GVCN THEO KHỐI =====
MON_GVCN_KHOI_123 = ['Toán', 'Tiếng Việt', 'Đạo đức', 'Tự nhiên & Xã hội', 'Hoạt Động Trải Nghiệm']
MON_GVCN_KHOI_45  = ['Toán', 'Tiếng Việt', 'Đạo đức', 'Khoa học', 'Lịch sử & Địa lý', 'Hoạt Động Trải Nghiệm']

# ===== DANH SÁCH GVCN (2 lớp/khối × 5 khối = 10 GVCN) =====
gvcn_configs = [
    # Khối 1
    ('0901000101', 'Nguyễn Thị Hoa',   'Nữ',  MON_GVCN_KHOI_123, '1A'),
    ('0901000102', 'Trần Thị Lan',     'Nữ',  MON_GVCN_KHOI_123, '1B'),
    # Khối 2
    ('0901000201', 'Lê Thị Mai',       'Nữ',  MON_GVCN_KHOI_123, '2A'),
    ('0901000202', 'Phạm Thị Hồng',   'Nữ',  MON_GVCN_KHOI_123, '2B'),
    # Khối 3
    ('0901000301', 'Hoàng Thị Yến',   'Nữ',  MON_GVCN_KHOI_123, '3A'),
    ('0901000302', 'Vũ Thị Thanh',    'Nữ',  MON_GVCN_KHOI_123, '3B'),
    # Khối 4
    ('0901000401', 'Đỗ Văn Nam',      'Nam', MON_GVCN_KHOI_45,  '4A'),
    ('0901000402', 'Bùi Thị Tuyết',   'Nữ',  MON_GVCN_KHOI_45,  '4B'),
    # Khối 5
    ('0901000501', 'Ngô Văn Hải',     'Nam', MON_GVCN_KHOI_45,  '5A'),
    ('0901000502', 'Đinh Thị Ngọc',   'Nữ',  MON_GVCN_KHOI_45,  '5B'),
]

# ===== DANH SÁCH GV BỘ MÔN =====
# Tiếng Anh: 2 GV (1 dạy khối 1-3, 1 dạy khối 4-5)
# Tin học: 1 GV (dạy khối 3-5)
# Âm nhạc: 1 GV (toàn trường)
# Mỹ thuật: 1 GV (toàn trường)
# GDTC: 1 GV (toàn trường)
gv_bomoN_configs = [
    ('0902000101', 'Nguyễn Văn Tú',   'Nam', 'Giáo viên bộ môn', ['Tiếng Anh']),
    ('0902000102', 'Lê Thị Phương',   'Nữ',  'Giáo viên bộ môn', ['Tiếng Anh']),
    ('0902000201', 'Trần Văn Khoa',   'Nam', 'Giáo viên bộ môn', ['Tin học']),
    ('0902000301', 'Phạm Thị Nhạc',   'Nữ',  'Giáo viên bộ môn', ['Âm nhạc']),
    ('0902000401', 'Hoàng Văn Họa',   'Nam', 'Giáo viên bộ môn', ['Mỹ thuật']),
    ('0902000501', 'Vũ Văn Thể',      'Nam', 'Giáo viên bộ môn', ['Giáo dục thể chất']),
]

print("=" * 80)
print("TẠO GIÁO VIÊN CHỦ NHIỆM & GIÁO VIÊN BỘ MÔN")
print("=" * 80)

print("\n>>> GIÁO VIÊN CHỦ NHIỆM (10 người - 2 lớp/khối)\n")
for sdt, hoten, gioitinh, mon_list, ten_lop in gvcn_configs:
    gv = tao_giaovien(sdt, hoten, gioitinh, 'Giáo viên chủ nhiệm', mon_list)
    gan_lop_chuyen_nhiem(gv, ten_lop)
    mon_str = ', '.join([m.TenMon for m in gv.MonGiangDay.all()])
    print(f"  ✓ {hoten:25} | Lớp CN: {ten_lop} | {sdt} | Mon: {mon_str}")

print("\n>>> GIÁO VIÊN BỘ MÔN CHUYÊN BIỆT (6 người)\n")
for sdt, hoten, gioitinh, chuc_vu, mon_list in gv_bomoN_configs:
    gv = tao_giaovien(sdt, hoten, gioitinh, chuc_vu, mon_list)
    mon_str = ', '.join([m.TenMon for m in gv.MonGiangDay.all()])
    print(f"  ✓ {hoten:25} | {sdt} | Mon: {mon_str}")

print("\n" + "=" * 80)
print("HOÀN THÀNH! Tổng kết:")
print(f"  - 10 Giáo viên chủ nhiệm (mỗi khối 2 lớp A, B)")
print(f"  - 6  Giáo viên bộ môn chuyên biệt")
print(f"  - Tất cả password: 123456")
print("=" * 80)

print("\nBẢNG TÀI KHOẢN GVCN:")
print(f"{'Họ tên':<26} {'Lớp':<5} {'Username':<13} {'Mật khẩu'}")
print("-" * 65)
for sdt, hoten, _, _, ten_lop in gvcn_configs:
    print(f"  {hoten:<24} {ten_lop:<5} {sdt:<13} 123456")

print("\nBẢNG TÀI KHOẢN GV BỘ MÔN:")
print(f"{'Họ tên':<26} {'Môn':<22} {'Username':<13} {'Mật khẩu'}")
print("-" * 75)
for sdt, hoten, _, _, mon_list in gv_bomoN_configs:
    print(f"  {hoten:<24} {', '.join(mon_list):<22} {sdt:<13} 123456")
