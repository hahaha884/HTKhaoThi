from django.db import models
from matrix.models import MaTran
from core.models import GiaoVien, NamHoc, MonHoc, Khoi
from question_bank.models import CauHoi
from django.utils import timezone
import datetime

class DeThi(models.Model):
    # Relational Data
    MaMaTran = models.ForeignKey(MaTran, on_delete=models.CASCADE)
    NguoiTao = models.ForeignKey(GiaoVien, on_delete=models.CASCADE, related_name='dethi_tao')
    NamHoc = models.ForeignKey(NamHoc, on_delete=models.SET_NULL, null=True, blank=True)
    MonHoc = models.ForeignKey(MonHoc, on_delete=models.SET_NULL, null=True, blank=True)
    Khoi = models.ForeignKey(Khoi, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Basic Information
    TenDe = models.CharField(max_length=255)
    HocKy = models.CharField(max_length=50, choices=[('Học kỳ 1', 'Học kỳ 1'), ('Học kỳ 2', 'Học kỳ 2')], default='Học kỳ 1')
    KyThi = models.CharField(max_length=100, choices=[
        ('Giữa kỳ', 'Giữa kỳ'),
        ('Cuối kỳ', 'Cuối kỳ'),
    ], default='Giữa kỳ')
    HinhThucTao = models.CharField(max_length=50, choices=[('Tự động', 'Tự động'), ('Thủ công', 'Thủ công')], default='Tự động')
    TongDiem = models.FloatField()
    
    # Workflow & Status
    TrangThai = models.CharField(max_length=50, choices=[
        ('Nháp', 'Nháp'),
        ('Đã nộp', 'Đã nộp'),
        ('Chính thức', 'Chính thức'),
        ('Đã xóa', 'Đã xóa')
    ], default='Nháp')
    
    # Tracking properties
    DeGoc = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='ban_sao')
    
    # Approval Flow
    NguoiDuyet = models.ForeignKey(GiaoVien, on_delete=models.SET_NULL, null=True, blank=True, related_name='dethi_duyet')
    ThoiGianGiaoDuyet = models.DateTimeField(null=True, blank=True)
    ThoiGianDuyet = models.DateTimeField(null=True, blank=True)
    TrangThaiDoc = models.CharField(max_length=50, choices=[('Chưa đọc', 'Chưa đọc'), ('Đã đọc', 'Đã đọc')], default='Chưa đọc')
    NguoiDoc = models.ForeignKey(GiaoVien, on_delete=models.SET_NULL, null=True, blank=True, related_name='dethi_doc')

    CreatedAt = models.DateTimeField(auto_now_add=True)
    UpdatedAt = models.DateTimeField(auto_now=True)

    @property
    def is_used(self):
        if hasattr(self, 'lich_thi') and self.lich_thi:
            today = timezone.now().date()
            now = timezone.now().time()
            if self.lich_thi.NgayThi < today:
                return True
            if self.lich_thi.NgayThi == today and self.lich_thi.GioKetThuc < now:
                return True
        return False
        
    @property
    def is_scheduled_future(self):
        if hasattr(self, 'lich_thi') and self.lich_thi:
            today = timezone.now().date()
            now = timezone.now().time()
            if self.lich_thi.NgayThi > today:
                return True
            if self.lich_thi.NgayThi == today and self.lich_thi.GioKetThuc >= now:
                return True
        return False

    class Meta:
        db_table = 'DE_THI'

class DeThi_CT(models.Model):
    MaDe = models.ForeignKey(DeThi, on_delete=models.CASCADE)
    MaCauHoi = models.ForeignKey(CauHoi, on_delete=models.CASCADE)
    ThuTuCau = models.IntegerField()
    DiemSo = models.FloatField()
    
    class Meta:
        db_table = 'DETHI_CT'

class LichSuPheDuyetDeThi(models.Model):
    MaDe = models.ForeignKey(DeThi, on_delete=models.CASCADE, related_name='lich_su')
    NguoiThucHien = models.ForeignKey(GiaoVien, on_delete=models.CASCADE)
    HanhDong = models.CharField(max_length=50) # Gửi duyệt, Phê duyệt, Từ chối
    ThoiGian = models.DateTimeField(auto_now_add=True)
    GhiChu = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'LICH_SU_PHE_DUYET_DE_THI'
