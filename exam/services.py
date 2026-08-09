import random
from django.db import transaction
from django.db.models import Count
from matrix.models import MaTran
from question_bank.models import CauHoi
from .models import DeThi, DeThi_CT


def _chon_cau_hoi_it_dung_nhat(pool_ids, so_luong):
    """
    Chọn ngẫu nhiên có trọng số từ pool, ưu tiên câu ít xuất hiện trong đề thi nhất.

    Thuật toán:
    1. Đếm số lần mỗi câu trong pool đã được dùng trong DeThi_CT.
    2. Gán trọng số nghịch đảo: câu dùng ít → trọng số cao hơn.
    3. Dùng random.choices (weighted) để chọn không trùng lặp.

    Đảm bảo:
    - Trong cùng 1 đề không có câu trùng.
    - Giữa các đề, câu ít dùng được ưu tiên, giảm lặp bất thường.
    - Vẫn có yếu tố ngẫu nhiên (không deterministic).
    - Không vi phạm cấu trúc ma trận.
    """
    if so_luong >= len(pool_ids):
        # Pool vừa đủ hoặc nhỏ hơn yêu cầu → trả toàn bộ (đã kiểm tra đủ ở trên)
        return list(pool_ids)

    # Đếm số lần xuất hiện trong lịch sử đề thi
    usage_qs = (
        DeThi_CT.objects
        .filter(MaCauHoi_id__in=pool_ids)
        .values('MaCauHoi_id')
        .annotate(so_lan=Count('id'))
    )
    usage_map = {row['MaCauHoi_id']: row['so_lan'] for row in usage_qs}

    # Trọng số: câu chưa dùng = max_usage+1, câu dùng nhiều = 1
    max_usage = max(usage_map.values()) if usage_map else 0
    weights = [max_usage + 1 - usage_map.get(cid, 0) for cid in pool_ids]

    # Chọn không trùng lặp bằng cách rút dần
    pool_list = list(pool_ids)
    chosen = []
    for _ in range(so_luong):
        idx = random.choices(range(len(pool_list)), weights=weights)[0]
        chosen.append(pool_list[idx])
        # Loại câu vừa chọn khỏi pool tạm để không trùng
        pool_list.pop(idx)
        weights.pop(idx)

    return chosen


class ExamGeneratorService:
    @staticmethod
    def generate_auto_exam(matran, thong_tin_de, user):
        """
        Sinh đề tự động dựa trên Ma Trận.
        Sử dụng weighted random ưu tiên câu ít dùng để giảm trùng lặp giữa các đề.
        """
        try:
            with transaction.atomic():
                # 1. Tạo vỏ Đề thi (Nháp)
                de_thi = DeThi.objects.create(
                    MaMaTran=matran,
                    NguoiTao=user,
                    NamHoc_id=thong_tin_de.get('nam_hoc'),
                    HocKy=thong_tin_de.get('hoc_ky'),
                    KyThi=thong_tin_de.get('ky_thi'),
                    MonHoc_id=thong_tin_de.get('mon_hoc'),
                    Khoi_id=thong_tin_de.get('khoi'),
                    TenDe=thong_tin_de.get('ten_de'),
                    TongDiem=matran.TongSoDiem,
                    HinhThucTao='Tự động',
                    TrangThai='Nháp'
                )

                thu_tu_cau = 1

                # 2. Quét từng dòng quy tắc trong Ma Trận
                for ct in matran.chi_tiet.all():

                    # 2.1: Truy vấn Ngân hàng theo đúng field của model CauHoi
                    # CT_MaTran.LoaiCauHoi lưu 'Trắc nghiệm' hoặc 'Tự luận'
                    # CauHoi.HinhThuc cũng lưu 'Trắc nghiệm' hoặc 'Tự luận'
                    pool_ids = list(
                        CauHoi.objects
                        .filter(
                            NoiDungKienThuc=ct.NoiDung,
                            MucDo=ct.MucDo,
                            HinhThuc=ct.LoaiCauHoi,
                            MonHoc_id=thong_tin_de.get('mon_hoc'),
                            Khoi_id=thong_tin_de.get('khoi')
                        )
                        .values_list('id', flat=True)
                    )

                    so_luong_can_lay = ct.SoLuongCau
                    diem_moi_cau = round(ct.Diem / so_luong_can_lay, 2) if so_luong_can_lay > 0 else 0

                    # 2.2: Conflict Detection
                    if len(pool_ids) < so_luong_can_lay:
                        raise Exception(
                            f"Ngân hàng câu hỏi không đủ! "
                            f"Yêu cầu {so_luong_can_lay} câu về '{ct.NoiDung.TenNoidung}' "
                            f"(Mức độ: {ct.MucDo}, Dạng: {ct.LoaiCauHoi}). "
                            f"Ngân hàng hiện chỉ có {len(pool_ids)} câu phù hợp."
                        )

                    # 2.3: Chọn ngẫu nhiên có trọng số — ưu tiên câu ít dùng nhất
                    cau_hoi_ids_chon = _chon_cau_hoi_it_dung_nhat(pool_ids, so_luong_can_lay)

                    # 2.4: Lưu vào Đề thi chi tiết
                    for cau_id in cau_hoi_ids_chon:
                        DeThi_CT.objects.create(
                            MaDe=de_thi,
                            MaCauHoi_id=cau_id,
                            ThuTuCau=thu_tu_cau,
                            DiemSo=diem_moi_cau
                        )
                        thu_tu_cau += 1

                return de_thi

        except Exception as e:
            raise Exception(str(e))


    @staticmethod
    def generate_manual_exam_shell(matran, thong_tin_de, user):
        """
        Sinh vỏ đề (các placeholder rỗng) để người dùng chọn thủ công
        """
        try:
            with transaction.atomic():
                de_thi = DeThi.objects.create(
                    MaMaTran=matran,
                    NguoiTao=user,
                    NamHoc_id=thong_tin_de.get('nam_hoc'),
                    HocKy=thong_tin_de.get('hoc_ky'),
                    KyThi=thong_tin_de.get('ky_thi'),
                    MonHoc_id=thong_tin_de.get('mon_hoc'),
                    Khoi_id=thong_tin_de.get('khoi'),
                    TenDe=thong_tin_de.get('ten_de'),
                    TongDiem=matran.TongSoDiem,
                    HinhThucTao='Thủ công',
                    TrangThai='Nháp'
                )
                
                # Ở hình thức thủ công, ta không sinh sẵn DeThi_CT.
                # Khi người dùng mở giao diện, hệ thống sẽ dựa vào MaTran để hiển thị các slot trống.
                return de_thi
                
        except Exception as e:
            raise Exception(str(e))
