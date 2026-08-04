import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import GiaoVien, MonHoc, Khoi

def create_totruong_to2():
    username = '0911111112'  # SĐT là username
    password = '123456'
    ho_ten = 'Tổ trưởng Tổ 2 - Nguyễn Thị B'

    # Tạo hoặc cập nhật User
    user, created = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.save()
    if created:
        print(f"Tao User moi: {username}")
    else:
        print(f"Cap nhat mat khau User: {username}")

    # Tạo hoặc cập nhật GiaoVien
    gv, gv_created = GiaoVien.objects.get_or_create(SDT=username, defaults={
        'user': user,
        'HoTen': ho_ten,
        'GioiTinh': 'Nữ',
        'ChucVu': 'Tổ trưởng chuyên môn',
        'TrangThai': 'Đang hoạt động',
    })

    if not gv_created:
        gv.user = user
        gv.HoTen = ho_ten
        gv.ChucVu = 'Tổ trưởng chuyên môn'
        gv.TrangThai = 'Đang hoạt động'
        gv.save()
        print("Cap nhat GiaoVien To truong To 2.")
    else:
        print("Tao GiaoVien To truong To 2.")

    # Gán môn học cho tổ trưởng tổ 2
    # Tổ 2 thường gồm: Toán, Tiếng Anh, Tin học, Âm nhạc, Mỹ thuật, Giáo dục thể chất
    ten_mon_to2 = ['Toán', 'Tiếng Anh', 'Tin học', 'Âm nhạc', 'Mỹ thuật', 'Giáo dục thể chất']
    mon_to2 = MonHoc.objects.filter(TenMon__in=ten_mon_to2)
    gv.MonGiangDay.set(mon_to2)
    
    # Gán khối phụ trách (Khối 2)
    khoi_2 = Khoi.objects.filter(TenKhoi='Khối 2').first()
    if khoi_2:
        gv.KhoiPhuTrach.set([khoi_2])
    
    gv.save()

    print("\n=== Thong tin tai khoan da tao ===")
    print(f"  Ho ten     : {gv.HoTen}")
    print(f"  Chuc vu    : {gv.ChucVu}")
    print(f"  Username   : {username}")
    print(f"  Password   : {password}")
    mon_str = ', '.join([m.TenMon for m in gv.MonGiangDay.all()])
    print(f"  Mon hoc    : {mon_str}")
    khoi_str = ', '.join([k.TenKhoi for k in gv.KhoiPhuTrach.all()])
    print(f"  Khoi phu trach : {khoi_str}")
    print(f"  Trang thai : {gv.TrangThai}")

if __name__ == '__main__':
    create_totruong_to2()
    print("\nDone!")
