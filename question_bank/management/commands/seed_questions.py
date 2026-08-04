"""
Django Management Command - Seed 150 câu hỏi mẫu đa dạng vào Ngân hàng câu hỏi.
Chạy: python manage.py seed_questions
"""
from django.core.management.base import BaseCommand
from question_bank.models import MachKienThuc, NoiDungKienThuc, CauHoi, DapAn
from core.models import GiaoVien
import random


NOI_DUNG_MCQ = [
    "Trong các phát biểu sau, phát biểu nào là ĐÚNG về <b>{chu_de}</b>?",
    "Đặc điểm nào dưới đây KHÔNG thuộc về <b>{chu_de}</b>?",
    "Khi học về <b>{chu_de}</b>, điều quan trọng nhất cần ghi nhớ là gì?",
    "Quan sát hình ảnh, em hãy cho biết nội dung nào liên quan đến <b>{chu_de}</b>?",
    "Ý nào sau đây MÔ TẢ ĐÚNG nhất về <b>{chu_de}</b>?",
    "Lựa chọn câu trả lời CHÍNH XÁC nhất về <b>{chu_de}</b>?",
    "Theo em, <b>{chu_de}</b> có đặc điểm gì nổi bật?",
    "Trong thực tế, <b>{chu_de}</b> thường được ứng dụng như thế nào?",
]

NOI_DUNG_TL = [
    "Em hãy trình bày khái niệm và đặc điểm của <b>{chu_de}</b>.",
    "Hãy phân tích vai trò của <b>{chu_de}</b> trong đời sống.",
    "Nêu ví dụ thực tế minh họa cho <b>{chu_de}</b> và giải thích.",
    "So sánh và nhận xét về <b>{chu_de}</b>. Rút ra kết luận.",
    "Em suy nghĩ như thế nào về tầm quan trọng của <b>{chu_de}</b>?",
]

DAP_AN_MCQ = [
    ["Đây là đáp án đúng - Phương án phù hợp với yêu cầu",
     "Phương án này chưa chính xác do thiếu một số yếu tố",
     "Đáp án gây nhầm lẫn nhưng không đầy đủ",
     "Phương án sai hoàn toàn so với yêu cầu đề bài"],
    ["Lựa chọn A là chính xác nhất trong các phương án",
     "Lựa chọn B có một phần đúng nhưng không hoàn toàn",
     "Lựa chọn C là sai do không đáp ứng điều kiện đề ra",
     "Lựa chọn D không liên quan đến nội dung câu hỏi"],
]


class Command(BaseCommand):
    help = 'Seed 150 câu hỏi mẫu đa dạng vào Ngân hàng câu hỏi'

    def handle(self, *args, **options):
        self.stdout.write("=== BẮT ĐẦU SEED 150 CÂU HỎI ===\n")

        nguoi_tao = GiaoVien.objects.first()
        if not nguoi_tao:
            self.stderr.write("❌ Chưa có GiaoVien nào. Dừng lại.")
            return
        self.stdout.write(f"👤 Người tạo: {nguoi_tao.HoTen}")

        # Lấy tất cả nội dung kiến thức
        ndkt_list = list(
            NoiDungKienThuc.objects.select_related(
                'MachKienThuc__MonHoc', 'MachKienThuc__Khoi'
            ).all()
        )

        if not ndkt_list:
            self.stderr.write("❌ Chưa có Nội dung kiến thức nào. Hãy tạo Mạch KT trước.")
            return

        self.stdout.write(f"📚 Số Nội dung KT tìm thấy: {len(ndkt_list)}")

        MUC_DO = ['Mức 1', 'Mức 2', 'Mức 3']
        DANG_MCQ = ['Trắc nghiệm']
        DANG_TL  = ['Tự luận']

        tong_them = 0
        muc_tieu = 150
        # Phân bổ: 120 trắc nghiệm + 30 tự luận
        mcq_count = 0
        tl_count = 0

        while tong_them < muc_tieu:
            # Lấy ngẫu nhiên 1 nội dung kiến thức
            ndkt = random.choice(ndkt_list)
            mach = ndkt.MachKienThuc
            mon  = mach.MonHoc
            khoi = mach.Khoi
            chu_de = ndkt.TenNoidung

            muc_do = random.choice(MUC_DO)

            # 80% trắc nghiệm, 20% tự luận
            is_mcq = (tong_them % 5 != 4)

            if is_mcq:
                noi_dung = random.choice(NOI_DUNG_MCQ).format(chu_de=chu_de)
                dang = 'Trắc nghiệm'
                hinh_thuc = 'Trắc nghiệm'
            else:
                noi_dung = random.choice(NOI_DUNG_TL).format(chu_de=chu_de)
                dang = 'Tự luận'
                hinh_thuc = 'Tự luận'

            cau_hoi = CauHoi.objects.create(
                NoiDungKienThuc=ndkt,
                MachKienThuc=mach,
                Khoi=khoi,
                MonHoc=mon,
                NguoiTao=nguoi_tao,
                HinhThuc=hinh_thuc,
                DangCauHoi=dang,
                MucDo=muc_do,
                NoiDungCauHoi=noi_dung,
                DapAnMau='Xem hướng dẫn chấm.' if not is_mcq else None
            )

            if is_mcq:
                dap_an_set = random.choice(DAP_AN_MCQ)
                for j, nd in enumerate(dap_an_set):
                    DapAn.objects.create(
                        CauHoi=cau_hoi,
                        ThuTu=j + 1,
                        NoiDung=f"{nd} ({muc_do} - {chu_de})",
                        LaDapAnDung=(j == 0)
                    )

            tong_them += 1

        tong_cau = CauHoi.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Đã thêm {tong_them} câu hỏi thành công!\n"
            f"📊 Tổng câu hỏi trong Ngân hàng: {tong_cau} câu"
        ))
