import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import GiaoVien

def create_bgh():
    username = '0999999999'
    password = '123456'
    
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password(password)
        user.save()
        print(f"Created User: {username}")
    else:
        print(f"User {username} already exists. Updating password.")
        user.set_password(password)
        user.save()

    gv, created = GiaoVien.objects.get_or_create(SDT=username, defaults={
        'user': user,
        'HoTen': 'Hiệu trưởng Nguyễn Văn A',
        'GioiTinh': 'Nam',
        'ChucVu': 'Hiệu trưởng',
        'TrangThai': 'Đang hoạt động'
    })
    
    if not created:
        gv.user = user
        gv.ChucVu = 'Hiệu trưởng'
        gv.save()
        print("Updated GiaoVien BGH.")
    else:
        print("Created GiaoVien BGH.")

if __name__ == '__main__':
    create_bgh()
    print("Done!")
