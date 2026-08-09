import os, django, random
import sys
sys.path.append('d:\\HT Khao Thi')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from core.models import GiaoVien, Khoi

teachers = list(GiaoVien.objects.all().order_by('id'))
khois = list(Khoi.objects.all().order_by('id')) # Khối 1, 2, 3, 4, 5

if len(khois) != 5:
    print("Error: Need exactly 5 Khối")
    sys.exit(1)

# Reset all Khối
for t in teachers:
    t.KhoiPhuTrach.clear()

# 1. Assign HT and HP
ht = teachers.pop(0)
ht.ChucVu = 'Hiệu trưởng'
ht.save()
ht.KhoiPhuTrach.add(khois[4]) # Khối 5

hp1 = teachers.pop(0)
hp1.ChucVu = 'Phó hiệu trưởng'
hp1.save()
hp1.KhoiPhuTrach.add(khois[3]) # Khối 4

hp2 = teachers.pop(0)
hp2.ChucVu = 'Phó hiệu trưởng'
hp2.save()
hp2.KhoiPhuTrach.add(khois[2]) # Khối 3

# 2. Distribute remaining to Khối 1-5 evenly
# Each Khối needs 1 TT, 1 TP, and the rest as GVCN/GVBM
per_khoi = len(teachers) // 5
remainder = len(teachers) % 5

def get_role_distribution(num_teachers):
    roles = ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']
    for _ in range(num_teachers - 2):
        roles.append(random.choices(['Giáo viên chủ nhiệm', 'Giáo viên bộ môn'], weights=[0.7, 0.3])[0])
    return roles

idx = 0
for i, k in enumerate(khois):
    # Calculate how many teachers for this Khối
    num = per_khoi + (1 if i < remainder else 0)
    
    if num < 2:
        print(f"Warning: Not enough teachers for {k.TenKhoi}")
        continue
        
    roles = get_role_distribution(num)
    
    for role in roles:
        t = teachers[idx]
        t.ChucVu = role
        t.KhoiPhuTrach.clear()
        t.KhoiPhuTrach.add(k)
        
        # Assign subjects based on role and grade
        if role == 'Giáo viên chủ nhiệm':
            if k.TenKhoi in ['Khối 4', 'Khối 5']:
                from core.models import MonHoc
                mons = MonHoc.objects.filter(TenMon__in=['Tiếng Việt', 'Toán', 'Đạo đức', 'Khoa học', 'Lịch sử & Địa lý', 'Hoạt Động Trải Nghiệm'])
            else:
                from core.models import MonHoc
                mons = MonHoc.objects.filter(TenMon__in=['Tiếng Việt', 'Toán', 'Đạo đức', 'Tự nhiên & Xã hội', 'Hoạt Động Trải Nghiệm'])
            t.MonGiangDay.set(mons)
        elif role == 'Giáo viên bộ môn':
            from core.models import MonHoc
            all_bm = list(MonHoc.objects.filter(TenMon__in=['Tiếng Anh', 'Giáo dục thể chất', 'Âm nhạc', 'Mỹ thuật', 'Tin học', 'Công nghệ']))
            t.MonGiangDay.set([random.choice(all_bm)])
        else:
            # Tổ trưởng / Tổ phó
            t.MonGiangDay.clear()
            
        t.save()
        idx += 1

print("Phân rã thành công!")
for k in khois:
    count = GiaoVien.objects.filter(KhoiPhuTrach=k).count()
    tt = GiaoVien.objects.filter(KhoiPhuTrach=k, ChucVu='Tổ trưởng chuyên môn').count()
    tp = GiaoVien.objects.filter(KhoiPhuTrach=k, ChucVu='Tổ phó chuyên môn').count()
    gv = count - tt - tp
    print(f"{k.TenKhoi}: Tổng {count} người (1 TT, 1 TP, {gv} GV)")

print(f"BGH: 1 HT (Khối 5), 2 HP (Khối 3, 4)")
