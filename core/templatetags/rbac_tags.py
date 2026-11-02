from django import template
from core.models import GiaoVien

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key) or dictionary.get(str(key)) or dictionary.get(int(key) if str(key).isdigit() else key)
    return None


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

@register.filter
def can_create_exam(user):
    if user.is_superuser:
        return True
    try:
        if user.giaovien.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
            return False
        return True
    except:
        return False
