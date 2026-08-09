import os, django, random
from faker import Faker
import sys
sys.path.append('d:\\HT Khao Thi')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from core.models import GiaoVien, MonHoc, Khoi

fake = Faker('vi_VN')
Faker.seed(42)

gvcn_mons_123 = list(MonHoc.objects.filter(TenMon__in=['Tiếng Việt', 'Toán', 'Đạo đức', 'Tự nhiên & Xã hội', 'Hoạt Động Trải Nghiệm']))
gvcn_mons_45 = list(MonHoc.objects.filter(TenMon__in=['Tiếng Việt', 'Toán', 'Đạo đức', 'Khoa học', 'Lịch sử & Địa lý', 'Hoạt Động Trải Nghiệm']))
all_bm = list(MonHoc.objects.filter(TenMon__in=['Tiếng Anh', 'Giáo dục thể chất', 'Âm nhạc', 'Mỹ thuật', 'Tin học', 'Công nghệ']))

for _ in range(20):
    gioi_tinh = random.choice(['Nam', 'Nữ'])
    hoten = fake.name_male() if gioi_tinh == 'Nam' else fake.name_female()
    sdt = '09' + str(random.randint(10000000, 99999999))
    while GiaoVien.objects.filter(SDT=sdt).exists():
        sdt = '09' + str(random.randint(10000000, 99999999))
        
    email = f"gv_{sdt}@example.com"
    chucvu = random.choices(['Giáo viên chủ nhiệm', 'Giáo viên bộ môn'], weights=[0.7, 0.3])[0]
    
    gv = GiaoVien.objects.create(
        user=None,
        HoTen=hoten,
        NgaySinh=fake.date_of_birth(minimum_age=22, maximum_age=55),
        GioiTinh=gioi_tinh,
        Email=email,
        SDT=sdt,
        ChucVu=chucvu,
        NgayBatDauChucVu=fake.date_between(start_date='-5y', end_date='today'),
        TrangThai='Chưa cấp tài khoản'
    )
    
    if chucvu == 'Giáo viên chủ nhiệm':
        gv.MonGiangDay.set(random.choice([gvcn_mons_123, gvcn_mons_45]))
    else:
        gv.MonGiangDay.set([random.choice(all_bm)])

print("Tạo thành công 20 giáo viên chưa cấp tài khoản!")
