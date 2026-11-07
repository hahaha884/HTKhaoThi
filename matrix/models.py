from django.db import models
from django.utils import timezone
from core.models import NamHoc, Khoi, MonHoc
from question_bank.models import NoiDungKienThuc, MachKienThuc

class MaTran(models.Model):
    NguoiTao = models.ForeignKey('core.GiaoVien', on_delete=models.CASCADE)
    TenMaTran = models.CharField(max_length=255)
    MoTa = models.TextField(null=True, blank=True)
    NamHoc = models.ForeignKey(NamHoc, on_delete=models.CASCADE, null=True, blank=True)
    HocKy = models.CharField(max_length=20, choices=[('Học kỳ 1', 'Học kỳ 1'), ('Học kỳ 2', 'Học kỳ 2')], null=True, blank=True)
    KyThi = models.CharField(max_length=50, choices=[('Giữa kỳ', 'Giữa kỳ'), ('Cuối kỳ', 'Cuối kỳ')], null=True, blank=True)
    MonHoc = models.ForeignKey(MonHoc, on_delete=models.CASCADE, null=True, blank=True)
    Khoi = models.ForeignKey(Khoi, on_delete=models.CASCADE, null=True, blank=True)
    
    TongSoCau = models.IntegerField(default=0)
    TongSoDiem = models.FloatField(default=0)
    TrangThai = models.CharField(max_length=50, default='Chờ duyệt')
    NgayCapNhat = models.DateTimeField(auto_now=True, null=True)

    # ===== DEADLINE FIELDS (BGH set sau khi duyệt) =====
    # Deadline Tổ chuyên môn nộp đề thi
    DeadlineNopDe = models.DateField(null=True, blank=True, help_text="Hạn nộp đề thi (BGH set sau khi duyệt ma trận)")
    # Deadline sửa (BGH set khi yêu cầu chỉnh sửa)
    DeadlineSuaDe = models.DateField(null=True, blank=True, help_text="Hạn sửa đề thi (BGH set khi yêu cầu sửa lại)")
    # Người set deadline
    NguoiSetDeadline = models.ForeignKey('core.GiaoVien', on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='matran_deadline_set', help_text="BGH đã set deadline")
    NgaySetDeadline = models.DateTimeField(null=True, blank=True, help_text="Thời điểm BGH set deadline")

    class Meta:
        db_table = 'MA_TRAN'
        unique_together = ('NamHoc', 'HocKy', 'KyThi', 'Khoi', 'MonHoc')

    @property
    def deadline_hien_tai(self):
        """Trả về deadline hiện tại (ưu tiên DeadlineSuaDe nếu có)."""
        return self.DeadlineSuaDe or self.DeadlineNopDe

    @property
    def deadline_status(self):
        """
        Trả về trạng thái deadline:
        - 'expired'  : đã hết hạn
        - 'urgent'   : còn < 2 ngày
        - 'ok'       : còn >= 2 ngày
        - None       : không có deadline
        """
        dl = self.deadline_hien_tai
        if not dl:
            return None
        today = timezone.localdate()
        delta = (dl - today).days
        if delta < 0:
            return 'expired'
        elif delta < 2:
            return 'urgent'
        return 'ok'

    @property
    def days_remaining(self):
        """Số ngày còn lại đến deadline (số âm nếu đã quá hạn)."""
        dl = self.deadline_hien_tai
        if not dl:
            return None
        today = timezone.localdate()
        return (dl - today).days


class CT_MaTran(models.Model):
    MaTran = models.ForeignKey(MaTran, on_delete=models.CASCADE, related_name='chi_tiet')
    MachKienThuc = models.ForeignKey(MachKienThuc, on_delete=models.CASCADE, null=True, blank=True)
    NoiDung = models.ForeignKey(NoiDungKienThuc, on_delete=models.CASCADE)
    MucDo = models.CharField(max_length=50)
    LoaiCauHoi = models.CharField(max_length=50)
    SoLuongCau = models.IntegerField()
    CauSo = models.CharField(max_length=255, help_text="Phân tách bằng dấu phẩy", null=True, blank=True)
    Diem = models.FloatField()
    TyLe = models.FloatField()
    class Meta:
        db_table = 'CT_MATRAN'

class LichSuPheDuyetMaTran(models.Model):
    MaTran = models.ForeignKey(MaTran, on_delete=models.CASCADE, related_name='lich_su')
    NguoiPheDuyet = models.ForeignKey('core.GiaoVien', on_delete=models.CASCADE)
    ThoiGian = models.DateTimeField(auto_now_add=True)
    TrangThai = models.CharField(max_length=50)
    GhiChu = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'LICH_SU_PHE_DUYET_MA_TRAN'


class DeadlineGiaoVien(models.Model):
    """
    TCM set deadline làm đề cho từng giáo viên,
    gắn với ma trận đã được duyệt.
    """
    MaTran = models.ForeignKey(MaTran, on_delete=models.CASCADE, related_name='deadline_gv')
    GiaoVien = models.ForeignKey('core.GiaoVien', on_delete=models.CASCADE, related_name='deadline_lam_de')
    NguoiSet = models.ForeignKey('core.GiaoVien', on_delete=models.CASCADE, related_name='deadline_set_boi_tcm')
    Deadline = models.DateField(help_text="Hạn chót GV phải nộp đề thi")
    GhiChu = models.TextField(null=True, blank=True)
    NgayTao = models.DateTimeField(auto_now_add=True)
    NgayCapNhat = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'DEADLINE_GIAO_VIEN'
        unique_together = ('MaTran', 'GiaoVien')

    @property
    def deadline_status(self):
        """
        Trạng thái deadline:
        - 'expired': đã hết hạn
        - 'urgent' : còn < 2 ngày
        - 'ok'     : còn >= 2 ngày
        """
        today = timezone.localdate()
        delta = (self.Deadline - today).days
        if delta < 0:
            return 'expired'
        elif delta < 2:
            return 'urgent'
        return 'ok'

    @property
    def days_remaining(self):
        today = timezone.localdate()
        return (self.Deadline - today).days
