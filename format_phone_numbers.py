import os, django, random
import sys
sys.path.append('d:\\HT Khao Thi')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from core.models import GiaoVien

prefixes = ['032', '033', '034', '035', '036', '037', '038', '039', 
            '070', '079', '077', '076', '078', 
            '083', '084', '085', '081', '082', 
            '090', '091', '092', '093', '094', '096', '097', '098', '099']

teachers = GiaoVien.objects.all()
existing_phones = set()

for t in teachers:
    while True:
        prefix = random.choice(prefixes)
        suffix = ''.join([str(random.randint(0, 9)) for _ in range(7)])
        new_phone = prefix + suffix
        
        if new_phone not in existing_phones:
            existing_phones.add(new_phone)
            t.SDT = new_phone
            t.save()
            break

print(f"Đã cập nhật định dạng số điện thoại cho {teachers.count()} giáo viên!")
