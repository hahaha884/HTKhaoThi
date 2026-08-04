# -*- coding: utf-8 -*-
import os, sys
import django
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import DeThi

all_de = DeThi.objects.all()
for d in all_de:
    print(f"ID={d.id} | {d.TrangThai!r} | {d.TrangThaiDoc!r} | {d.TenDe[:40]}")

# Fix da nop + da doc -> chua doc
DA_NOP = '\u0110\u00e3 n\u1ed9p'
DA_DOC = '\u0110\u00e3 \u0111\u1ecdc'
CHUA_DOC = 'Ch\u01b0a \u0111\u1ecdc'

fixed = DeThi.objects.filter(TrangThai=DA_NOP, TrangThaiDoc=DA_DOC).update(
    TrangThaiDoc=CHUA_DOC,
    NguoiDoc=None
)
print(f"Fixed {fixed} records")
