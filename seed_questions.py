"""
Script seed dữ liệu câu hỏi mẫu cho Ngân hàng câu hỏi.
Chạy bằng lệnh: python seed_questions.py
"""
import os, django, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from question_bank.models import MachKienThuc, NoiDungKienThuc, CauHoi, DapAn, NhomCauHoi
from core.models import GiaoVien, MonHoc, Khoi
from matrix.models import MaTran, CT_MaTran

def seed():
    print("=== BẮT ĐẦU SEED DỮ LIỆU CÂU HỎI ===\n")
    
    # Lấy tài khoản giáo viên đầu tiên để gán làm người tạo
    nguoi_tao = GiaoVien.objects.first()
    if not nguoi_tao:
        print("❌ Chưa có GiaoVien nào trong DB. Dừng lại.")
        return
    print(f"✅ Người tạo: {nguoi_tao.HoTen}")

    # Lấy các ma trận đã duyệt để biết cần seed câu hỏi dạng gì
    ma_tran_list = MaTran.objects.filter(TrangThai='Đã duyệt').select_related('MonHoc', 'Khoi')
    
    if not ma_tran_list.exists():
        print("⚠️  Không có Ma trận nào ở trạng thái 'Đã duyệt'. Seed toàn bộ NoiDungKienThuc.")
    
    tong_da_them = 0
    
    # Lấy tất cả NoiDungKienThuc và seed câu hỏi cho mỗi loại
    for ndkt in NoiDungKienThuc.objects.select_related('MachKienThuc__MonHoc', 'MachKienThuc__Khoi').all():
        mach = ndkt.MachKienThuc
        mon = mach.MonHoc
        khoi = mach.Khoi
        
        # Seed cho mỗi mức độ và dạng câu hỏi
        combos = [
            ('Mức 1', 'Trắc nghiệm'),
            ('Mức 2', 'Trắc nghiệm'),
            ('Mức 3', 'Trắc nghiệm'),
            ('Mức 1', 'Tự luận'),
            ('Mức 2', 'Tự luận'),
        ]
        
        for muc_do, dang_cau_hoi in combos:
            # Kiểm tra đã có đủ 5 câu chưa (để không bị thiếu khi sinh đề)
            so_hien_co = CauHoi.objects.filter(
                NoiDungKienThuc=ndkt,
                MucDo=muc_do,
                DangCauHoi=dang_cau_hoi
            ).count()
            
            so_can_them = max(0, 5 - so_hien_co)
            
            for i in range(1, so_can_them + 1):
                idx = so_hien_co + i
                noi_dung = f"[{muc_do} - {dang_cau_hoi}] Câu hỏi số {idx} về nội dung <b>{ndkt.TenNoidung}</b> ({mon.TenMon} - {khoi.TenKhoi})?"
                
                cau_hoi = CauHoi.objects.create(
                    NoiDungKienThuc=ndkt,
                    MachKienThuc=mach,
                    Khoi=khoi,
                    MonHoc=mon,
                    NguoiTao=nguoi_tao,
                    HinhThuc='Trắc nghiệm' if dang_cau_hoi == 'Trắc nghiệm' else 'Tự luận',
                    DangCauHoi=dang_cau_hoi,
                    MucDo=muc_do,
                    NoiDungCauHoi=noi_dung,
                    DapAnMau='Đáp án mẫu' if dang_cau_hoi == 'Tự luận' else None
                )
                
                # Tạo đáp án cho câu trắc nghiệm
                if dang_cau_hoi == 'Trắc nghiệm':
                    for j, label in enumerate(['A', 'B', 'C', 'D']):
                        DapAn.objects.create(
                            CauHoi=cau_hoi,
                            ThuTu=j+1,
                            NoiDung=f"Đáp án {label}: Lựa chọn {j+1} cho câu hỏi về {ndkt.TenNoidung}",
                            LaDapAnDung=(j == 0)  # Đáp án A luôn đúng trong dữ liệu mẫu
                        )
                
                tong_da_them += 1
        
        print(f"  ✅ {ndkt.TenNoidung} ({mon.TenMon}, {khoi.TenKhoi}): đã bổ sung câu hỏi")
    
    print(f"\n=== HOÀN TẤT! Đã thêm {tong_da_them} câu hỏi vào Ngân hàng ===")
    
    # Thống kê tổng
    tong_cau = CauHoi.objects.count()
    print(f"📊 Tổng câu hỏi trong Ngân hàng hiện tại: {tong_cau} câu")

if __name__ == '__main__':
    seed()
