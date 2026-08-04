import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from matrix.models import CT_MaTran
from django.db.models import Count

print("=== GIA TRI LoaiCauHoi TRONG MA TRAN ===")
for row in CT_MaTran.objects.values('LoaiCauHoi').annotate(n=Count('id')).order_by('-n'):
    print(f"  '{row['LoaiCauHoi']}': {row['n']} dong")

print("\n=== GIA TRI DangCauHoi TRONG CAU HOI ===")
from question_bank.models import CauHoi
for row in CauHoi.objects.values('DangCauHoi').annotate(n=Count('id')).order_by('-n'):
    print(f"  '{row['DangCauHoi']}': {row['n']} cau")
