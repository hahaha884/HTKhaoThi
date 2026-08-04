"""
Command fix câu hỏi thiếu đáp án hoặc đáp án rỗng.
Chạy: python manage.py fix_missing_answers
"""
from django.core.management.base import BaseCommand
from question_bank.models import CauHoi, DapAn
import random

NHAN = ['A', 'B', 'C', 'D']

MAN_DAP_AN = {
    'Mức 1': [
        "Câu trả lời đúng và đầy đủ theo nội dung đã học",
        "Câu trả lời chưa đúng, còn thiếu sót quan trọng",
        "Câu trả lời sai, lẫn lộn với khái niệm khác",
        "Câu trả lời sai hoàn toàn, không phù hợp nội dung",
    ],
    'Mức 2': [
        "Đây là đáp án chính xác và đầy đủ",
        "Đáp án này đúng một phần nhưng chưa đủ ý",
        "Đáp án này bị nhầm lẫn với kiến thức khác",
        "Đáp án này không liên quan đến câu hỏi",
    ],
    'Mức 3': [
        "Vận dụng đúng kiến thức để đưa ra kết quả chính xác",
        "Áp dụng sai bước dẫn đến kết quả không đúng",
        "Hiểu sai yêu cầu, đưa ra câu trả lời lệch hướng",
        "Hoàn toàn sai, không vận dụng được kiến thức đã học",
    ],
}


class Command(BaseCommand):
    help = 'Sửa câu hỏi thiếu đáp án hoặc đáp án rỗng'

    def handle(self, *args, **options):
        self.stdout.write("=== FIX THIẾU / RỖNG ĐÁP ÁN ===\n")

        da_fix = 0
        bo_qua = 0

        # --- Xử lý câu hỏi TRẮC NGHIỆM ---
        cau_hoi_tn = CauHoi.objects.filter(
            DangCauHoi__in=['Trắc nghiệm', 'Trắc nghiệm 4 lựa chọn']
        ).prefetch_related('dap_ans')

        for cau_hoi in cau_hoi_tn:
            dap_ans = list(cau_hoi.dap_ans.all())
            chu_de = (
                cau_hoi.NoiDungKienThuc.TenNoidung
                if cau_hoi.NoiDungKienThuc
                else "nội dung đã học"
            )
            muc_do = cau_hoi.MucDo or 'Mức 1'
            templates = MAN_DAP_AN.get(muc_do, MAN_DAP_AN['Mức 1'])

            # Kiểm tra: đủ 4 đáp án VÀ không có đáp án rỗng
            da_du = (
                len(dap_ans) >= 4
                and all(da.NoiDung and da.NoiDung.strip() for da in dap_ans)
                and any(da.LaDapAnDung for da in dap_ans)
            )

            if da_du:
                bo_qua += 1
                continue

            # Xóa cũ và tạo lại
            cau_hoi.dap_ans.all().delete()

            idx_dung = random.randint(0, 3)
            for j, nhan in enumerate(NHAN):
                la_dung = (j == idx_dung)
                nd = templates[j]
                DapAn.objects.create(
                    CauHoi=cau_hoi,
                    ThuTu=j + 1,
                    NoiDung=f"{nd} ({chu_de[:40]})" ,
                    LaDapAnDung=la_dung
                )

            da_fix += 1

        # --- Xử lý câu hỏi TỰ LUẬN thiếu DapAnMau ---
        fix_tl = 0
        cau_hoi_tl = CauHoi.objects.filter(HinhThuc='Tự luận')
        for cau_hoi in cau_hoi_tl:
            if not cau_hoi.DapAnMau or not cau_hoi.DapAnMau.strip():
                chu_de = (
                    cau_hoi.NoiDungKienThuc.TenNoidung
                    if cau_hoi.NoiDungKienThuc
                    else "nội dung câu hỏi"
                )
                cau_hoi.DapAnMau = (
                    f"Học sinh cần trình bày đầy đủ, rõ ràng về {chu_de}. "
                    f"Giáo viên chấm theo thang điểm rubric đã quy định."
                )
                cau_hoi.save(update_fields=['DapAnMau'])
                fix_tl += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Đã fix {da_fix} câu trắc nghiệm (thiếu/rỗng đáp án).\n"
            f"✅ Đã fix {fix_tl} câu tự luận (thiếu đáp án mẫu).\n"
            f"⏭  Bỏ qua {bo_qua} câu trắc nghiệm đã đủ."
        ))
