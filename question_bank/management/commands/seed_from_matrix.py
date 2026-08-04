"""
Seed câu hỏi dựa TRỰC TIẾP vào từng dòng CT_MaTran.
Đảm bảo mỗi dòng ma trận có đủ câu hỏi phù hợp.
Chạy: python manage.py seed_from_matrix
"""
from django.core.management.base import BaseCommand
from question_bank.models import NoiDungKienThuc, CauHoi, DapAn, MachKienThuc
from core.models import GiaoVien
from matrix.models import CT_MaTran
import random


NOI_DUNG_MCQ = [
    "Câu {idx}: Trong các phương án sau, phương án nào ĐÚNG về <b>{chu_de}</b>?",
    "Câu {idx}: Phương án nào MÔ TẢ CHÍNH XÁC nhất về <b>{chu_de}</b>?",
    "Câu {idx}: Chọn đáp án ĐÚNG: Kiến thức liên quan đến <b>{chu_de}</b> là gì?",
    "Câu {idx}: Điều nào sau đây KHÔNG phải đặc điểm của <b>{chu_de}</b>?",
    "Câu {idx}: Kết quả đúng khi áp dụng kiến thức <b>{chu_de}</b> là?",
    "Câu {idx}: Theo nội dung đã học về <b>{chu_de}</b>, phương án nào phù hợp?",
    "Câu {idx}: Vận dụng hiểu biết về <b>{chu_de}</b>, em chọn đáp án nào?",
    "Câu {idx}: Quan sát và cho biết điều gì liên quan đến <b>{chu_de}</b>?",
]

NOI_DUNG_TL = [
    "Câu {idx}: Hãy trình bày hiểu biết của em về <b>{chu_de}</b>.",
    "Câu {idx}: Phân tích và nêu ví dụ về <b>{chu_de}</b>.",
    "Câu {idx}: Em hãy giải thích tầm quan trọng của <b>{chu_de}</b> trong thực tế.",
    "Câu {idx}: Nêu nhận xét và đánh giá của em về <b>{chu_de}</b>.",
]


class Command(BaseCommand):
    help = 'Seed câu hỏi trực tiếp từ từng dòng CT_MaTran để đảm bảo đủ câu hỏi'

    def handle(self, *args, **options):
        self.stdout.write("=== SEED TỪ CT_MATRAN ===\n")

        nguoi_tao = GiaoVien.objects.first()
        if not nguoi_tao:
            self.stderr.write("❌ Không tìm thấy GiaoVien.")
            return

        # Lấy tất cả dòng CT_MaTran
        ct_list = CT_MaTran.objects.select_related(
            'NoiDung__MachKienThuc__MonHoc',
            'NoiDung__MachKienThuc__Khoi'
        ).all()

        if not ct_list.exists():
            self.stderr.write("❌ Không có dòng CT_MaTran nào.")
            return

        tong_them = 0

        for ct in ct_list:
            ndkt = ct.NoiDung
            muc_do = ct.MucDo
            dang = ct.LoaiCauHoi  # ví dụ: 'Trắc nghiệm' hoặc 'Tự luận'
            so_yeu_cau = ct.SoLuongCau
            mach = ndkt.MachKienThuc
            mon = mach.MonHoc
            khoi = mach.Khoi
            chu_de = ndkt.TenNoidung

            # Đếm số câu hiện có khớp ĐÚNG với dòng ma trận này
            so_hien_co = CauHoi.objects.filter(
                NoiDungKienThuc=ndkt,
                MucDo=muc_do,
                DangCauHoi=dang
            ).count()

            # Cần thêm ít nhất đủ số câu yêu cầu + buffer 3 câu dự phòng
            can_them = max(0, so_yeu_cau + 3 - so_hien_co)

            if can_them == 0:
                self.stdout.write(
                    f"  ✅ Đủ rồi ({so_hien_co}/{so_yeu_cau}): {chu_de[:50]} | {muc_do} | {dang}"
                )
                continue

            la_tu_luan = dang.lower() in ['tự luận', 'tu luan']

            for i in range(can_them):
                idx = so_hien_co + i + 1
                if la_tu_luan:
                    nd = random.choice(NOI_DUNG_TL).format(idx=idx, chu_de=chu_de)
                    hinh_thuc = 'Tự luận'
                else:
                    nd = random.choice(NOI_DUNG_MCQ).format(idx=idx, chu_de=chu_de)
                    hinh_thuc = 'Trắc nghiệm'

                cau_hoi = CauHoi.objects.create(
                    NoiDungKienThuc=ndkt,
                    MachKienThuc=mach,
                    Khoi=khoi,
                    MonHoc=mon,
                    NguoiTao=nguoi_tao,
                    HinhThuc=hinh_thuc,
                    DangCauHoi=dang,
                    MucDo=muc_do,
                    NoiDungCauHoi=nd,
                    DapAnMau='Xem hướng dẫn chấm.' if la_tu_luan else None
                )

                if not la_tu_luan:
                    dap_ans = [
                        ("Đây là đáp án ĐÚNG", True),
                        ("Phương án này gần đúng nhưng chưa đầy đủ", False),
                        ("Phương án này có yếu tố đúng nhưng bị nhầm lẫn", False),
                        ("Phương án hoàn toàn không phù hợp", False),
                    ]
                    random.shuffle(dap_ans)  # Trộn để đáp án đúng không luôn ở vị trí A
                    # Nhưng vẫn cần đảm bảo có 1 đáp án đúng
                    # Ta giữ đáp án đúng ở vị trí random
                    for j, (noi_dung_da, la_dung) in enumerate(dap_ans):
                        DapAn.objects.create(
                            CauHoi=cau_hoi,
                            ThuTu=j + 1,
                            NoiDung=f"{noi_dung_da} ({chu_de[:30]}...)" if len(chu_de) > 30 else f"{noi_dung_da} ({chu_de})",
                            LaDapAnDung=la_dung
                        )

                tong_them += 1

            self.stdout.write(
                f"  ➕ Thêm {can_them} câu: {chu_de[:50]} | {muc_do} | {dang}"
            )

        tong_cau = CauHoi.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ XONG! Đã thêm {tong_them} câu mới.\n"
            f"📊 Tổng kho: {tong_cau} câu hỏi"
        ))
