import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import MonHoc, Khoi
from question_bank.models import MachKienThuc, NoiDungKienThuc

df = pd.read_excel(r'd:\Downloads\mach_kien_thuc_tieu_hoc.xlsx')

success_count = 0
for index, row in df.iterrows():
    try:
        mon_hoc_str = str(row['Môn học']).strip()
        khoi_str = str(row['Khối lớp']).strip()
        mach_str = str(row['Mạch kiến thức']).strip()
        noidung_str = str(row['Nội dung kiến thức']).strip()
        
        if pd.isna(row['Môn học']) or mon_hoc_str == 'nan' or mon_hoc_str == '':
            continue
            
        mon_hoc, _ = MonHoc.objects.get_or_create(TenMon=mon_hoc_str)
        khoi, _ = Khoi.objects.get_or_create(TenKhoi=khoi_str)
        
        mach, _ = MachKienThuc.objects.get_or_create(
            MonHoc=mon_hoc,
            Khoi=khoi,
            TenMach=mach_str
        )
        
        if noidung_str and noidung_str != 'nan':
            # Handle multiple contents separated by newline or bullet points if needed
            # But based on the image, each row is one NoiDung or multiple NoiDung in one cell?
            # Looking at the image, each row is ONE combination, but the text might be long.
            NoiDungKienThuc.objects.get_or_create(
                MachKienThuc=mach,
                TenNoidung=noidung_str[:250] # truncated to fit max_length if needed
            )
            success_count += 1
    except Exception as e:
        print(f"Error at row {index}: {e}")

print(f"Imported {success_count} content items successfully!")
