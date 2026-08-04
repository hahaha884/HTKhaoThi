import os
import django
import random
from faker import Faker

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.models import GiaoVien, Khoi, MonHoc

fake = Faker('vi_VN')

def generate_mock_teachers():
    roles = [
        'Tổ trưởng chuyên môn',
        'Tổ phó chuyên môn',
        'Giáo viên chủ nhiệm',
        'Giáo viên bộ môn'
    ]
    
    khois = Khoi.objects.all()
    mon_hocs = list(MonHoc.objects.all())
    
    if not khois or not mon_hocs:
        print("Cần có dữ liệu Khối và Môn học trước khi tạo Giáo viên.")
        return
        
    created_count = 0
    
    for khoi in khois:
        # Lấy các môn học áp dụng cho khối này (nếu được thiết lập, hoặc lấy ngẫu nhiên)
        mons_for_khoi = [m for m in mon_hocs if khoi in m.KhoiApDung.all()]
        if not mons_for_khoi:
            mons_for_khoi = mon_hocs  # Fallback nếu chưa map
            
        for role in roles:
            for _ in range(10):
                # Tạo số điện thoại unique
                sdt = fake.unique.phone_number()
                if len(sdt) > 15:
                    sdt = sdt[:15]
                    
                gioi_tinh = random.choice(['Nam', 'Nữ'])
                
                gv = GiaoVien(
                    HoTen=fake.name(),
                    NgaySinh=fake.date_of_birth(minimum_age=23, maximum_age=60),
                    GioiTinh=gioi_tinh,
                    Email=fake.unique.email(),
                    SDT=sdt,
                    ChucVu=role,
                    TrangThai='Đang hoạt động'
                )
                gv.save()
                
                # Thêm khối phụ trách
                gv.KhoiPhuTrach.add(khoi)
                
                # Thêm ngẫu nhiên 1-3 môn học
                num_mons = random.randint(1, min(3, len(mons_for_khoi)))
                selected_mons = random.sample(mons_for_khoi, num_mons)
                for m in selected_mons:
                    gv.MonGiangDay.add(m)
                    
                created_count += 1
                
    print(f"Đã tạo thành công {created_count} giáo viên.")

if __name__ == '__main__':
    generate_mock_teachers()
