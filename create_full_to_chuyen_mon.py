import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import GiaoVien, MonHoc, Khoi

def create_to_member(sdt, hoten, chuc_vu, ten_khoi, ten_mon_list):
    """Tạo Tổ trưởng hoặc Tổ phó chuyên môn"""
    password = '123456'
    
    # Tạo/cập nhật User
    user, created = User.objects.get_or_create(username=sdt)
    user.set_password(password)
    user.save()
    
    # Tạo/cập nhật GiaoVien
    gv, gv_created = GiaoVien.objects.get_or_create(SDT=sdt, defaults={
        'user': user,
        'HoTen': hoten,
        'GioiTinh': 'Nữ' if 'Thị' in hoten else 'Nam',
        'ChucVu': chuc_vu,
        'TrangThai': 'Đang hoạt động',
    })
    
    if not gv_created:
        gv.user = user
        gv.HoTen = hoten
        gv.ChucVu = chuc_vu
        gv.TrangThai = 'Đang hoạt động'
        gv.save()
    
    # Gán môn giảng dạy
    mon_hocs = MonHoc.objects.filter(TenMon__in=ten_mon_list)
    gv.MonGiangDay.set(mon_hocs)
    
    # Gán khối phụ trách
    khoi = Khoi.objects.filter(TenKhoi=ten_khoi).first()
    if khoi:
        gv.KhoiPhuTrach.set([khoi])
    
    gv.save()
    return gv

# Cấu hình đầy đủ: Tổ trưởng + Tổ phó cho 5 khối
configs = [
    # KHỐI 1
    {
        'sdt': '0911111111',
        'hoten': 'Tổ trưởng Khối 1 - Lê Thị C',
        'chuc_vu': 'Tổ trưởng chuyên môn',
        'khoi': 'Khối 1',
        'mon_list': ['Tiếng Việt', 'Đạo đức', 'Tự nhiên & Xã hội', 'Hoạt Động Trải Nghiệm', 'Âm nhạc']
    },
    {
        'sdt': '0911111121',
        'hoten': 'Tổ phó Khối 1 - Nguyễn Văn G',
        'chuc_vu': 'Tổ phó chuyên môn',
        'khoi': 'Khối 1',
        'mon_list': ['Tiếng Việt', 'Đạo đức', 'Tự nhiên & Xã hội', 'Hoạt Động Trải Nghiệm', 'Mỹ thuật']
    },
    
    # KHỐI 2
    {
        'sdt': '0911111112',
        'hoten': 'Tổ trưởng Khối 2 - Nguyễn Thị B',
        'chuc_vu': 'Tổ trưởng chuyên môn',
        'khoi': 'Khối 2',
        'mon_list': ['Toán', 'Tiếng Anh', 'Tin học', 'Âm nhạc', 'Mỹ thuật', 'Giáo dục thể chất']
    },
    {
        'sdt': '0911111122',
        'hoten': 'Tổ phó Khối 2 - Trần Văn H',
        'chuc_vu': 'Tổ phó chuyên môn',
        'khoi': 'Khối 2',
        'mon_list': ['Toán', 'Tiếng Anh', 'Tin học', 'Giáo dục thể chất']
    },
    
    # KHỐI 3
    {
        'sdt': '0911111113',
        'hoten': 'Tổ trưởng Khối 3 - Phạm Văn D',
        'chuc_vu': 'Tổ trưởng chuyên môn',
        'khoi': 'Khối 3',
        'mon_list': ['Tiếng Việt', 'Đạo đức', 'Tự nhiên & Xã hội', 'Hoạt Động Trải Nghiệm', 'Giáo dục thể chất']
    },
    {
        'sdt': '0911111123',
        'hoten': 'Tổ phó Khối 3 - Lê Thị I',
        'chuc_vu': 'Tổ phó chuyên môn',
        'khoi': 'Khối 3',
        'mon_list': ['Tiếng Việt', 'Đạo đức', 'Tự nhiên & Xã hội', 'Âm nhạc', 'Mỹ thuật']
    },
    
    # KHỐI 4
    {
        'sdt': '0911111114',
        'hoten': 'Tổ trưởng Khối 4 - Hoàng Thị E',
        'chuc_vu': 'Tổ trưởng chuyên môn',
        'khoi': 'Khối 4',
        'mon_list': ['Toán', 'Khoa học', 'Lịch sử & Địa lý', 'Tin học', 'Âm nhạc', 'Mỹ thuật']
    },
    {
        'sdt': '0911111124',
        'hoten': 'Tổ phó Khối 4 - Vũ Văn K',
        'chuc_vu': 'Tổ phó chuyên môn',
        'khoi': 'Khối 4',
        'mon_list': ['Toán', 'Khoa học', 'Lịch sử & Địa lý', 'Tin học']
    },
    
    # KHỐI 5
    {
        'sdt': '0911111115',
        'hoten': 'Tổ trưởng Khối 5 - Vũ Văn F',
        'chuc_vu': 'Tổ trưởng chuyên môn',
        'khoi': 'Khối 5',
        'mon_list': ['Toán', 'Tiếng Anh', 'Khoa học', 'Lịch sử & Địa lý', 'Tin học', 'Giáo dục thể chất']
    },
    {
        'sdt': '0911111125',
        'hoten': 'Tổ phó Khối 5 - Đỗ Thị L',
        'chuc_vu': 'Tổ phó chuyên môn',
        'khoi': 'Khối 5',
        'mon_list': ['Toán', 'Tiếng Anh', 'Khoa học', 'Lịch sử & Địa lý', 'Âm nhạc']
    }
]

print("=" * 80)
print("TAO DAY DU TAI KHOAN TO CHUYEN MON (TO TRUONG + TO PHO) CHO 5 KHOI")
print("=" * 80)
print()

for cfg in configs:
    gv = create_to_member(
        cfg['sdt'], 
        cfg['hoten'], 
        cfg['chuc_vu'],
        cfg['khoi'], 
        cfg['mon_list']
    )
    
    icon = "✓ TO TRUONG" if gv.ChucVu == 'Tổ trưởng chuyên môn' else "✓ TO PHO   "
    print(f"{icon} | {cfg['khoi']} | {gv.HoTen}")
    print(f"           Username: {cfg['sdt']} | Password: 123456")
    mon_str = ', '.join([m.TenMon for m in gv.MonGiangDay.all()])
    print(f"           Mon: {mon_str}")
    print()

print("=" * 80)
print("HOAN THANH! Da tao 10 tai khoan: 5 To truong + 5 To pho cho 5 khoi.")
print()
print("DANH SACH TAI KHOAN:")
print("-" * 80)
print("Khoi | Chuc vu      | Username    | Password")
print("-" * 80)
for cfg in configs:
    chuc_vu_short = "To truong" if cfg['chuc_vu'] == 'Tổ trưởng chuyên môn' else "To pho   "
    print(f"{cfg['khoi']:5} | {chuc_vu_short:12} | {cfg['sdt']:11} | 123456")
print("-" * 80)
