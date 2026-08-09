import os, django, random
import sys
sys.path.append('d:\\HT Khao Thi')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from core.models import GiaoVien, MonHoc, Khoi

gvcn_mons_123 = ['Tiếng Việt', 'Toán', 'Đạo đức', 'Tự nhiên & Xã hội', 'Hoạt Động Trải Nghiệm']
gvcn_mons_45 = ['Tiếng Việt', 'Toán', 'Đạo đức', 'Khoa học', 'Lịch sử & Địa lý', 'Hoạt Động Trải Nghiệm']
gvbm_mons_all = ['Tiếng Anh', 'Giáo dục thể chất', 'Âm nhạc', 'Mỹ thuật']
gvbm_mons_345 = ['Tin học', 'Công nghệ']

# Fetch MonHoc objects
def get_mon_objects(names):
    return list(MonHoc.objects.filter(TenMon__in=names))

mon_123 = get_mon_objects(gvcn_mons_123)
mon_45 = get_mon_objects(gvcn_mons_45)
mon_bm_all = get_mon_objects(gvbm_mons_all)
mon_bm_345 = get_mon_objects(gvbm_mons_345)
all_bm = mon_bm_all + mon_bm_345

khoi_123 = list(Khoi.objects.filter(TenKhoi__in=['Khối 1', 'Khối 2', 'Khối 3']))
khoi_45 = list(Khoi.objects.filter(TenKhoi__in=['Khối 4', 'Khối 5']))
all_khoi = list(Khoi.objects.all())

teachers = GiaoVien.objects.all()

for t in teachers:
    if t.ChucVu == 'Giáo viên chủ nhiệm':
        # Must not have KhoiPhuTrach
        t.KhoiPhuTrach.clear()
        
        # Determine grade from LopHoc if possible
        lop = t.lophoc_set.first()
        is_45 = False
        if lop:
            if lop.MaKhoi.TenKhoi in ['Khối 4', 'Khối 5']:
                is_45 = True
        else:
            is_45 = random.choice([True, False])
            
        t.MonGiangDay.set(mon_45 if is_45 else mon_123)
        print(f"Fixed GVCN: {t.HoTen} - Môn: {[m.TenMon for m in t.MonGiangDay.all()]}")
        
    elif t.ChucVu == 'Giáo viên bộ môn':
        t.KhoiPhuTrach.clear()
        
        current_bms = [m for m in t.MonGiangDay.all() if m in all_bm]
        if current_bms:
            t.MonGiangDay.set([current_bms[0]])
        else:
            t.MonGiangDay.set([random.choice(all_bm)])
            
        print(f"Fixed GVBM: {t.HoTen} - Môn: {[m.TenMon for m in t.MonGiangDay.all()]}")
        
    elif t.ChucVu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
        # If they are Tổ khối (have exactly 1 Khối phụ trách or created as such)
        if t.KhoiPhuTrach.count() == 1:
            t.MonGiangDay.clear()
            print(f"Fixed Tổ Khối: {t.HoTen} - Khối: {[k.TenKhoi for k in t.KhoiPhuTrach.all()]}")
        elif t.KhoiPhuTrach.count() > 1:
            # Tổ bộ môn
            current_bms = [m for m in t.MonGiangDay.all() if m in all_bm]
            if current_bms:
                chosen_mon = current_bms[0]
            else:
                chosen_mon = random.choice(all_bm)
                
            t.MonGiangDay.set([chosen_mon])
            # Set their Khối phụ trách correctly
            if chosen_mon in mon_bm_345:
                t.KhoiPhuTrach.set(Khoi.objects.filter(TenKhoi__in=['Khối 3', 'Khối 4', 'Khối 5']))
            else:
                t.KhoiPhuTrach.set(all_khoi)
                
            print(f"Fixed Tổ Bộ Môn: {t.HoTen} - Môn: {chosen_mon.TenMon} - Khối: {[k.TenKhoi for k in t.KhoiPhuTrach.all()]}")
        else:
            pass
            
    elif t.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng', 'Nhân viên văn thư']:
        t.KhoiPhuTrach.clear()
        t.MonGiangDay.clear()
