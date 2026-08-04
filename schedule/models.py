from django.db import models
from core.models import NamHoc, Khoi, MonHoc, GiaoVien, LopHoc
from exam.models import DeThi


CA_THI_CHOICES = [
    ('Buổi sáng', 'Buổi sáng'),
    ('Buổi chiều', 'Buổi chiều'),
]

HOC_KY_CHOICES = [
    ('Học kỳ 1', 'Học kỳ 1'),
    ('Học kỳ 2', 'Học kỳ 2'),
]

KY_THI_CHOICES = [
    ('Giữa kỳ', 'Giữa kỳ'),
    ('Cuối kỳ', 'Cuối kỳ'),
]


class LichThi(models.Model):
    NamHoc = models.ForeignKey(NamHoc, on_delete=models.CASCADE, null=True, blank=True)
    Khoi = models.ForeignKey(Khoi, on_delete=models.CASCADE)
    MonHoc = models.ForeignKey(MonHoc, on_delete=models.CASCADE)
    HocKy = models.CharField(max_length=50, choices=HOC_KY_CHOICES, default='Học kỳ 1')
    KyThi = models.CharField(max_length=100, choices=KY_THI_CHOICES, default='Giữa kỳ')
    CaThi = models.CharField(max_length=20, choices=CA_THI_CHOICES)
    NgayThi = models.DateField()
    GioBatDau = models.TimeField()
    GioKetThuc = models.TimeField()
    DeThi = models.OneToOneField(
        DeThi,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lich_thi',
    )
    GhiChu = models.TextField(blank=True, null=True)
    NguoiTao = models.ForeignKey(
        GiaoVien,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lich_thi_tao',
    )
    CreatedAt = models.DateTimeField(auto_now_add=True)
    UpdatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'LICH_THI'
        # Không trùng: cùng Khối + Ca + Ngày thi
        unique_together = [('Khoi', 'CaThi', 'NgayThi')]

    def __str__(self):
        return f"{self.Khoi} - {self.MonHoc} - {self.CaThi} ({self.NgayThi})"

    @property
    def can_edit_or_delete(self):
        from datetime import date
        today = date.today()
        if self.NgayThi < today:
            return False
        if (self.NgayThi - today).days < 7:
            return False
        return True

class PhanCongGiamThi(models.Model):
    LichThi = models.ForeignKey(LichThi, on_delete=models.CASCADE, related_name='phan_cong_set')
    LopHoc = models.ForeignKey(LopHoc, on_delete=models.CASCADE)
    
    GiamThi1 = models.ForeignKey(
        GiaoVien, on_delete=models.SET_NULL, null=True, blank=True, related_name='giam_thi_1_set'
    )
    GiamThi2 = models.ForeignKey(
        GiaoVien, on_delete=models.SET_NULL, null=True, blank=True, related_name='giam_thi_2_set'
    )
    
    # Dùng cho các trường hợp mời giám thị ngoài hoặc giám thị THCS (ví dụ Khối 5)
    GiamThiTHCS = models.CharField(max_length=255, null=True, blank=True)
    
    GhiChu = models.TextField(blank=True, null=True)
    CreatedAt = models.DateTimeField(auto_now_add=True)
    UpdatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PHANCONG_GIAMTHI'
        unique_together = [('LichThi', 'LopHoc')]

    def __str__(self):
        return f"Phân công: {self.LichThi} - Phòng: {self.LopHoc.TenLop}"

    @property
    def can_edit(self):
        from datetime import date
        import django.utils.timezone as tz
        today = date.today()
        if self.LichThi.NgayThi < today:
            return False
        if self.LichThi.NgayThi == today:
            now = tz.localtime(tz.now()).time()
            if self.LichThi.GioBatDau <= now:
                return False
        return True

    @property
    def can_delete(self):
        from datetime import date
        import django.utils.timezone as tz
        today = date.today()
        if self.LichThi.NgayThi < today:
            return False
        if self.LichThi.NgayThi == today:
            now = tz.localtime(tz.now()).time()
            if self.LichThi.GioBatDau <= now:
                return False
        days_until_exam = (self.LichThi.NgayThi - today).days
        if days_until_exam < 5:
            return False
        return True
