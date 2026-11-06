from django.db import models
from django.contrib.auth.models import User

from datetime import date

class NamHoc(models.Model):
    TenNamHoc = models.CharField(max_length=50, unique=True)
    NgayBatDau = models.DateField()
    NgayKetThuc = models.DateField()
    
    HKI_BatDau = models.DateField(null=True, blank=True)
    HKI_KetThuc = models.DateField(null=True, blank=True)
    GiuaKI_BatDau = models.DateField(null=True, blank=True)
    GiuaKI_KetThuc = models.DateField(null=True, blank=True)
    CuoiKI_BatDau = models.DateField(null=True, blank=True)
    CuoiKI_KetThuc = models.DateField(null=True, blank=True)
    
    HKII_BatDau = models.DateField(null=True, blank=True)
    HKII_KetThuc = models.DateField(null=True, blank=True)
    GiuaKII_BatDau = models.DateField(null=True, blank=True)
    GiuaKII_KetThuc = models.DateField(null=True, blank=True)
    CuoiKII_BatDau = models.DateField(null=True, blank=True)
    CuoiKII_KetThuc = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'NAM_HOC'
        
    @property
    def trang_thai(self):
        today = date.today()
        if today < self.NgayBatDau:
            return 'Sắp diễn ra'
        elif self.NgayBatDau <= today <= self.NgayKetThuc:
            return 'Đang diễn ra'
        else:
            return 'Đã kết thúc'

    def __str__(self): return self.TenNamHoc

class Khoi(models.Model):
    TenKhoi = models.CharField(max_length=50)
    class Meta:
        db_table = 'KHOI'
    def __str__(self): return self.TenKhoi

class MonHoc(models.Model):
    TenMon = models.CharField(max_length=100, unique=True)
    KhoiApDung = models.ManyToManyField('Khoi', blank=True)
    MoTa = models.TextField(blank=True, null=True)
    TrangThai = models.CharField(max_length=50, default='Đang hoạt động')

    class Meta:
        db_table = 'MON_HOC'
    def __str__(self): return self.TenMon

class GiaoVien(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    HoTen = models.CharField(max_length=100)
    NgaySinh = models.DateField(null=True, blank=True)
    GioiTinh = models.CharField(max_length=10, choices=[('Nam', 'Nam'), ('Nữ', 'Nữ')])
    Email = models.EmailField(max_length=100, null=True, blank=True)
    SDT = models.CharField(max_length=15, unique=True)
    MonGiangDay = models.ManyToManyField('MonHoc', blank=True)
    KhoiPhuTrach = models.ManyToManyField('Khoi', blank=True, related_name='to_truong_set')
    ChucVu = models.CharField(max_length=50, choices=[('Hiệu trưởng', 'Hiệu trưởng'), ('Phó hiệu trưởng', 'Phó hiệu trưởng'), ('Tổ trưởng chuyên môn', 'Tổ trưởng chuyên môn'), ('Tổ phó chuyên môn', 'Tổ phó chuyên môn'), ('Giáo viên chủ nhiệm', 'Giáo viên chủ nhiệm'), ('Giáo viên bộ môn', 'Giáo viên bộ môn'), ('Nhân viên văn thư', 'Nhân viên văn thư')], default='Giáo viên bộ môn')
    NgayBatDauChucVu = models.DateField(null=True, blank=True)
    NgayKetThucChucVu = models.DateField(null=True, blank=True)
    TrangThai = models.CharField(max_length=50, default='Chưa cấp tài khoản')
    
    class Meta:
        db_table = 'GIAO_VIEN'
        
    def has_tcm_permission(self, khoi_id, mon_id):
        """
        Checks if this TCM has permission for a specific grade block and subject.
        They have permission if:
        1. The block (khoi_id) is in their KhoiPhuTrach.
        2. And either the subject (mon_id) is in their MonGiangDay,
           or it is taught by any GVCN of that block.
        """
        if self.ChucVu not in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
            return False
            
        try:
            khoi_id = int(khoi_id)
        except (ValueError, TypeError):
            return False
            
        try:
            mon_id = int(mon_id)
        except (ValueError, TypeError):
            return False
            
        if not self.KhoiPhuTrach.filter(id=khoi_id).exists():
            return False
            
        if self.MonGiangDay.filter(id=mon_id).exists():
            return True
            
        # Inherit subjects from GVCNs of this block
        gvcn_subjects = self.__class__.objects.filter(
            ChucVu='Giáo viên chủ nhiệm'
        ).filter(
            models.Q(lophoc__MaKhoi_id=khoi_id) | 
            models.Q(phanconggiangday__MaLop__MaKhoi_id=khoi_id)
        ).values_list('MonGiangDay__id', flat=True).distinct()
        
        return mon_id in gvcn_subjects

    def __str__(self): return self.HoTen

class LopHoc(models.Model):
    MaNamHoc = models.ForeignKey(NamHoc, on_delete=models.CASCADE)
    MaKhoi = models.ForeignKey(Khoi, on_delete=models.CASCADE)
    GVCN = models.ForeignKey(GiaoVien, on_delete=models.SET_NULL, null=True, blank=True)
    TenLop = models.CharField(max_length=50)
    SiSoToiDa = models.IntegerField(default=35)
    class Meta:
        db_table = 'LOP_HOC'

class PhanCongGiangDay(models.Model):
    MaGV = models.ForeignKey(GiaoVien, on_delete=models.CASCADE)
    MaLop = models.ForeignKey(LopHoc, on_delete=models.CASCADE)
    class Meta:
        db_table = 'PHANCONG_GIANGDAY'


class ThongBao(models.Model):
    LOAI_CHOICES = [
        ('info', 'Thông tin'),
        ('warning', 'Cảnh báo'),
        ('danger', 'Khẩn cấp'),
        ('success', 'Thành công'),
    ]

    NguoiNhan = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='thong_bao_nhan')
    VaiTro = models.CharField(max_length=50, blank=True, null=True, help_text="BGH, TCM, GIAO_VIEN, ALL")
    TieuDe = models.CharField(max_length=255)
    NoiDung = models.TextField()
    Loai = models.CharField(max_length=20, choices=LOAI_CHOICES, default='info')
    Icon = models.CharField(max_length=100, default='fas fa-bell')
    LienKet = models.CharField(max_length=255, blank=True, null=True)
    DaDoc = models.BooleanField(default=False)
    NguoiDaDoc = models.ManyToManyField(User, blank=True, related_name='thong_bao_da_doc_set')
    RefKey = models.CharField(max_length=150, blank=True, null=True, db_index=True)
    NgayTao = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'THONG_BAO'
        ordering = ['-NgayTao']

    def __str__(self):
        return self.TieuDe

    def is_read_by(self, user):
        if not user or not user.is_authenticated:
            return False
        if self.NguoiNhan_id == user.id:
            return self.DaDoc
        return self.NguoiDaDoc.filter(id=user.id).exists()

    def mark_as_read(self, user):
        if not user or not user.is_authenticated:
            return
        if self.NguoiNhan_id == user.id:
            self.DaDoc = True
            self.save(update_fields=['DaDoc'])
        else:
            self.NguoiDaDoc.add(user)

