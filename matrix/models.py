from django.db import models
from core.models import GiaoVien, NamHoc, Khoi, MonHoc
from question_bank.models import NoiDungKienThuc, MachKienThuc

class MaTran(models.Model):
    NguoiTao = models.ForeignKey(GiaoVien, on_delete=models.CASCADE)
    TenMaTran = models.CharField(max_length=255)
    MoTa = models.TextField(null=True, blank=True)
    NamHoc = models.ForeignKey(NamHoc, on_delete=models.CASCADE, null=True, blank=True)
    HocKy = models.CharField(max_length=20, choices=[('Học kỳ 1', 'Học kỳ 1'), ('Học kỳ 2', 'Học kỳ 2')], null=True, blank=True)
    KyThi = models.CharField(max_length=50, choices=[('Giữa kỳ', 'Giữa kỳ'), ('Cuối kỳ', 'Cuối kỳ')], null=True, blank=True)
    MonHoc = models.ForeignKey(MonHoc, on_delete=models.CASCADE, null=True, blank=True)
    Khoi = models.ForeignKey(Khoi, on_delete=models.CASCADE, null=True, blank=True)
    
    TongSoCau = models.IntegerField(default=0)
    TongSoDiem = models.FloatField(default=0)
    TrangThai = models.CharField(max_length=50, default='Nháp')
    NgayCapNhat = models.DateTimeField(auto_now=True, null=True)
    
    class Meta:
        db_table = 'MA_TRAN'
        unique_together = ('NamHoc', 'HocKy', 'KyThi', 'Khoi', 'MonHoc')

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
    NguoiPheDuyet = models.ForeignKey(GiaoVien, on_delete=models.CASCADE)
    ThoiGian = models.DateTimeField(auto_now_add=True)
    TrangThai = models.CharField(max_length=50)
    GhiChu = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'LICH_SU_PHE_DUYET_MA_TRAN'
