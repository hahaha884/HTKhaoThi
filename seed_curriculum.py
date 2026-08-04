import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Khoi, MonHoc
from question_bank.models import MachKienThuc, NoiDungKienThuc

def seed_data():
    # 1. Tạo Khối
    khois = {}
    for i in range(1, 6):
        k, created = Khoi.objects.get_or_create(TenKhoi=f"Khối {i}")
        khois[i] = k
        print(f"{'Created' if created else 'Found'} {k.TenKhoi}")

    # 2. Tạo Môn Học
    mon_toan, _ = MonHoc.objects.get_or_create(TenMon="Toán")
    mon_tv, _ = MonHoc.objects.get_or_create(TenMon="Tiếng Việt")
    
    # 3. Seed Mạch và Nội dung cho Toán
    toan_machs = {
        "Số và phép tính": ["Số tự nhiên", "Phân số", "Số thập phân", "Cộng trừ nhân chia"],
        "Hình học và Đo lường": ["Hình phẳng", "Hình khối", "Đại lượng đo lường"],
        "Thống kê và Xác suất": ["Thu thập số liệu", "Biểu đồ", "Khả năng xảy ra"],
        "Thực hành và trải nghiệm": ["Vận dụng thực tế"]
    }
    
    for khoi_i, k_obj in khois.items():
        for mach_name, noidungs in toan_machs.items():
            mach, _ = MachKienThuc.objects.get_or_create(
                Khoi=k_obj,
                MonHoc=mon_toan,
                TenMach=mach_name
            )
            for nd_name in noidungs:
                NoiDungKienThuc.objects.get_or_create(
                    MachKienThuc=mach,
                    TenNoidung=nd_name
                )
                
    print("Seeded Toán curriculum.")

    # 4. Seed Mạch và Nội dung cho Tiếng Việt
    tv_machs = {
        "Kiến thức tiếng Việt": ["Ngữ âm và chữ viết", "Từ vựng", "Ngữ pháp"],
        "Kiến thức văn học": ["Đọc hiểu văn bản", "Cảm thụ văn học"],
        "Kỹ năng Đọc": ["Đọc thành tiếng", "Đọc thầm"],
        "Kỹ năng Viết": ["Viết chính tả", "Viết đoạn văn", "Viết bài văn"],
        "Kỹ năng Nói và Nghe": ["Trình bày ý kiến", "Nghe và phản hồi"]
    }
    
    for khoi_i, k_obj in khois.items():
        for mach_name, noidungs in tv_machs.items():
            mach, _ = MachKienThuc.objects.get_or_create(
                Khoi=k_obj,
                MonHoc=mon_tv,
                TenMach=mach_name
            )
            for nd_name in noidungs:
                NoiDungKienThuc.objects.get_or_create(
                    MachKienThuc=mach,
                    TenNoidung=nd_name
                )
                
    print("Seeded Tiếng Việt curriculum.")
    print("Done!")

if __name__ == "__main__":
    seed_data()
