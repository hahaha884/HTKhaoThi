from django import template
from core.models import GiaoVien

register = template.Library()

@register.filter
def is_admin(user):
    if user.is_superuser:
        return True
    try:
        if user.giaovien.ChucVu == 'Nhân viên văn thư':
            return True
    except:
        pass
    return False

@register.filter
def is_bgh(user):
    if user.is_superuser:
        return True
    try:
        if user.giaovien.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
            return True
    except:
        pass
    return False

@register.filter
def is_to_chuyen_mon(user):
    try:
        if user.giaovien.ChucVu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
            return True
    except:
        pass
    return False

@register.filter
def is_khao_thi(user):
    if user.is_superuser:
        return True
    try:
        if user.giaovien.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng', 'Tổ trưởng chuyên môn', 'Tổ phó chuyên môn', 'Giáo viên', 'Giáo viên bộ môn', 'Giáo viên chủ nhiệm']:
            return True
    except:
        pass
    return False
