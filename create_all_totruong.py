import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import GiaoVien, MonHoc, Khoi

def create_totruong(sdt, hoten, ten_khoi, ten_mon_list):
    """Tạo tổ trưởng chuyên môn cho một khối"""
    password = '123456'
    
    # Tạo/cập nhật User
    user, created = User.objects.get_or_create(username=sdt)
    user.set_password(password)
    user.save()
    
    # Tạo/cập nhật GiaoVien
    gv, gv_created = GiaoVien.objects.get_or_create(SDT=sdt, defaults={
        'user': user,
        'HoTen': hoten,
        'GioiTinh': 'Nữ',
        'ChucVu': 'Tổ trưởng chuyên môn',
        'TrangThai': 'Đang hoạt động',
    })
    
    if not gv_created:
        gv.user = user
        gv.HoTen = hoten
        gv.ChucVu = 'Tổ trưởng chuyên môn'
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

# Cấu hình tổ trưởng cho từng khối
# Lưu ý: Chia môn theo quy chế của trường. Đây là ví dụ phân tổ:
# - Tổ 1 (Khối 1): Tiếng Việt, Đạo đức, Tự nhiên & Xã hội, HĐTN
# - Tổ 2 (Khối 2): Toán, Tiếng Anh, Tin học, Âm nhạc, Mỹ thuật, GDTC (đã có)
# - Tổ 3 (Khối 3): tương tự Tổ 1
# - Tổ 4 (Khối 4): Toán, Khoa học, Lịch sử & Địa lý, Tin học
# - Tổ 5 (Khối 5): tương tự Tổ 4

configs = [
    {
        'sdt': '0911111111',
        'hoten': 'Tổ trưởng Tổ 1 - Khối 1 - Lê Thị C',
        'khoi': 'Khối 1',
        'mon_list': ['Tiếng Việt', 'Đạo đức', 'Tự nhiên & Xã hội', 'Hoạt Động Trải Nghiệm', 'Âm nhạc', 'Mỹ thuật']
    },
    {
        'sdt': '0911111112',  # Đã tạo trước đó
        'hoten': 'Tổ trưởng Tổ 2 - Khối 2 - Nguyễn Thị B',
        'khoi': 'Khối 2',
        'mon_list': ['Toán', 'Tiếng Anh', 'Tin học', 'Âm nhạc', 'Mỹ thuật', 'Giáo dục thể chất']
    },
    {
        'sdt': '0911111113',
        'hoten': 'Tổ trưởng Tổ 3 - Khối 3 - Phạm Văn D',
        'khoi': 'Khối 3',
        'mon_list': ['Tiếng Việt', 'Đạo đức', 'Tự nhiên & Xã hội', 'Hoạt Động Trải Nghiệm', 'Giáo dục thể chất']
    },
    {
        'sdt': '0911111114',
        'hoten': 'Tổ trưởng Tổ 4 - Khối 4 - Hoàng Thị E',
        'khoi': 'Khối 4',
        'mon_list': ['Toán', 'Khoa học', 'Lịch sử & Địa lý', 'Tin học', 'Âm nhạc', 'Mỹ thuật']
    },
    {
        'sdt': '0911111115',
        'hoten': 'Tổ trưởng Tổ 5 - Khối 5 - Vũ Văn F',
        'khoi': 'Khối 5',
        'mon_list': ['Toán', 'Khoa học', 'Lịch sử & Địa lý', 'Tin học', 'Tiếng Anh', 'Giáo dục thể chất']
    }
]

print("=== TAO TAI KHOAN TO TRUONG CHO CAC KHOI ===\n")

for cfg in configs:
    gv = create_totruong(cfg['sdt'], cfg['hoten'], cfg['khoi'], cfg['mon_list'])
    
    print(f"✓ {gv.HoTen}")
    print(f"  - Username   : {cfg['sdt']}")
    print(f"  - Password   : 123456")
    print(f"  - Khoi       : {cfg['khoi']}")
    mon_str = ', '.join([m.TenMon for m in gv.MonGiangDay.all()])
    print(f"  - Mon        : {mon_str}")
    print()

print("Done! Tat ca to truong da duoc tao/cap nhat.")
print("\nLuu y: Neu mon hoc khong ton tai trong he thong, vui long them vao truoc.")
