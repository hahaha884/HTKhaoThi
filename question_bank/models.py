from django.db import models
from core.models import MonHoc, Khoi, GiaoVien

class MachKienThuc(models.Model):
    MonHoc = models.ForeignKey(MonHoc, on_delete=models.CASCADE)
    Khoi = models.ForeignKey(Khoi, on_delete=models.CASCADE)
    TenMach = models.CharField(max_length=255)
    class Meta:
        db_table = 'MACH_KIEN_THUC'

class NoiDungKienThuc(models.Model):
    MachKienThuc = models.ForeignKey(MachKienThuc, on_delete=models.CASCADE)
    TenNoidung = models.CharField(max_length=255)
    class Meta:
        db_table = 'ND_KIEN_THUC'

class NhomCauHoi(models.Model):
    TenNhom = models.CharField(max_length=255)
    Khoi = models.ForeignKey(Khoi, on_delete=models.CASCADE, null=True)
    MonHoc = models.ForeignKey(MonHoc, on_delete=models.CASCADE, null=True)
    MachKienThuc = models.ForeignKey(MachKienThuc, on_delete=models.CASCADE, null=True)
    NoiDungKienThuc = models.ForeignKey(NoiDungKienThuc, on_delete=models.CASCADE, null=True)
    NoiDungChung = models.TextField(null=True, blank=True)
    MoTa = models.TextField(null=True, blank=True)
    HinhAnh = models.ImageField(upload_to='questions/groups/', null=True, blank=True)
    NguoiTao = models.ForeignKey(GiaoVien, on_delete=models.CASCADE, null=True)
    class Meta:
        db_table = 'NHOM_CAU_HOI'

class CauHoi(models.Model):
    MUC_DO_CHOICES = [('Mức 1', 'Mức 1'), ('Mức 2', 'Mức 2'), ('Mức 3', 'Mức 3')]
    NhomCauHoi = models.ForeignKey(NhomCauHoi, on_delete=models.CASCADE, null=True, blank=True, related_name='cau_hois')
    Khoi = models.ForeignKey(Khoi, on_delete=models.CASCADE, null=True)
    MonHoc = models.ForeignKey(MonHoc, on_delete=models.CASCADE, null=True)
    MachKienThuc = models.ForeignKey(MachKienThuc, on_delete=models.CASCADE, null=True)
    NoiDungKienThuc = models.ForeignKey(NoiDungKienThuc, on_delete=models.CASCADE, null=True)
    NguoiTao = models.ForeignKey(GiaoVien, on_delete=models.CASCADE)
    HinhThuc = models.CharField(max_length=50, default='Trắc nghiệm')
    DangCauHoi = models.CharField(max_length=50, default='MCQ')
    MucDo = models.CharField(max_length=50, choices=MUC_DO_CHOICES)
    NoiDungCauHoi = models.TextField()
    HinhAnh = models.ImageField(upload_to='questions/', null=True, blank=True)
    DapAnMau = models.TextField(null=True, blank=True)
    # New field for deadline
    Deadline = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = 'CAU_HOI'

class DapAn(models.Model):
    CauHoi = models.ForeignKey(CauHoi, on_delete=models.CASCADE, related_name='dap_ans')
    ThuTu = models.IntegerField(default=0)
    NoiDungTrai = models.TextField(null=True, blank=True)
    HinhAnhTrai = models.ImageField(upload_to='questions/answers/left/', null=True, blank=True)
    NoiDung = models.TextField(null=True, blank=True)
    HinhAnh = models.ImageField(upload_to='questions/answers/', null=True, blank=True)
    LaDapAnDung = models.BooleanField(default=False)
    class Meta:
        db_table = 'DAP_AN'
