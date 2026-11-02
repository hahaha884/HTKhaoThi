from django.db import migrations
from datetime import date


def seed_namhoc(apps, schema_editor):
    NamHoc = apps.get_model('core', 'NamHoc')
    data = [
        {
            'TenNamHoc': '2023-2024',
            'NgayBatDau': date(2023, 9, 5),
            'NgayKetThuc': date(2024, 5, 31),
            'HKI_BatDau': date(2023, 9, 5),
            'HKI_KetThuc': date(2024, 1, 15),
            'GiuaKI_BatDau': date(2023, 10, 25),
            'GiuaKI_KetThuc': date(2023, 11, 10),
            'CuoiKI_BatDau': date(2023, 12, 20),
            'CuoiKI_KetThuc': date(2024, 1, 10),
            'HKII_BatDau': date(2024, 1, 16),
            'HKII_KetThuc': date(2024, 5, 31),
            'GiuaKII_BatDau': date(2024, 3, 15),
            'GiuaKII_KetThuc': date(2024, 3, 30),
            'CuoiKII_BatDau': date(2024, 5, 5),
            'CuoiKII_KetThuc': date(2024, 5, 20),
        },
        {
            'TenNamHoc': '2024-2025',
            'NgayBatDau': date(2024, 9, 5),
            'NgayKetThuc': date(2025, 5, 31),
            'HKI_BatDau': date(2024, 9, 5),
            'HKI_KetThuc': date(2025, 1, 15),
            'GiuaKI_BatDau': date(2024, 10, 25),
            'GiuaKI_KetThuc': date(2024, 11, 10),
            'CuoiKI_BatDau': date(2024, 12, 20),
            'CuoiKI_KetThuc': date(2025, 1, 10),
            'HKII_BatDau': date(2025, 1, 16),
            'HKII_KetThuc': date(2025, 5, 31),
            'GiuaKII_BatDau': date(2025, 3, 15),
            'GiuaKII_KetThuc': date(2025, 3, 30),
            'CuoiKII_BatDau': date(2025, 5, 5),
            'CuoiKII_KetThuc': date(2025, 5, 20),
        },
        {
            'TenNamHoc': '2025-2026',
            'NgayBatDau': date(2025, 9, 5),
            'NgayKetThuc': date(2026, 5, 31),
            'HKI_BatDau': date(2025, 9, 5),
            'HKI_KetThuc': date(2026, 1, 15),
            'GiuaKI_BatDau': date(2025, 10, 25),
            'GiuaKI_KetThuc': date(2025, 11, 10),
            'CuoiKI_BatDau': date(2025, 12, 20),
            'CuoiKI_KetThuc': date(2026, 1, 10),
            'HKII_BatDau': date(2026, 1, 16),
            'HKII_KetThuc': date(2026, 5, 31),
            'GiuaKII_BatDau': date(2026, 3, 15),
            'GiuaKII_KetThuc': date(2026, 3, 30),
            'CuoiKII_BatDau': date(2026, 5, 5),
            'CuoiKII_KetThuc': date(2026, 5, 20),
        },
        {
            'TenNamHoc': '2026-2027',
            'NgayBatDau': date(2026, 9, 5),
            'NgayKetThuc': date(2027, 5, 31),
            'HKI_BatDau': date(2026, 9, 5),
            'HKI_KetThuc': date(2027, 1, 15),
            'GiuaKI_BatDau': date(2026, 10, 25),
            'GiuaKI_KetThuc': date(2026, 11, 10),
            'CuoiKI_BatDau': date(2026, 12, 20),
            'CuoiKI_KetThuc': date(2027, 1, 10),
            'HKII_BatDau': date(2027, 1, 16),
            'HKII_KetThuc': date(2027, 5, 31),
            'GiuaKII_BatDau': date(2027, 3, 15),
            'GiuaKII_KetThuc': date(2027, 3, 30),
            'CuoiKII_BatDau': date(2027, 5, 5),
            'CuoiKII_KetThuc': date(2027, 5, 20),
        },
        {
            'TenNamHoc': '2027-2028',
            'NgayBatDau': date(2027, 9, 5),
            'NgayKetThuc': date(2028, 5, 31),
            'HKI_BatDau': date(2027, 9, 5),
            'HKI_KetThuc': date(2028, 1, 15),
            'GiuaKI_BatDau': date(2027, 10, 25),
            'GiuaKI_KetThuc': date(2027, 11, 10),
            'CuoiKI_BatDau': date(2027, 12, 20),
            'CuoiKI_KetThuc': date(2028, 1, 10),
            'HKII_BatDau': date(2028, 1, 16),
            'HKII_KetThuc': date(2028, 5, 31),
            'GiuaKII_BatDau': date(2028, 3, 15),
            'GiuaKII_KetThuc': date(2028, 3, 30),
            'CuoiKII_BatDau': date(2028, 5, 5),
            'CuoiKII_KetThuc': date(2028, 5, 20),
        },
    ]
    for item in data:
        NamHoc.objects.update_or_create(TenNamHoc=item['TenNamHoc'], defaults=item)


def reverse_seed(apps, schema_editor):
    NamHoc = apps.get_model('core', 'NamHoc')
    NamHoc.objects.filter(TenNamHoc__in=['2023-2024', '2024-2025', '2025-2026', '2026-2027', '2027-2028']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_alter_giaovien_chucvu'),
    ]

    operations = [
        migrations.RunPython(seed_namhoc, reverse_seed),
    ]

