from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import NamHoc
from datetime import datetime
from .decorators import admin_required


@login_required
def schoolyear_list(request):
    schoolyears = NamHoc.objects.all().order_by('-NgayBatDau')
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        schoolyears = schoolyears.filter(TenNamHoc__icontains=search_query)
        
    if status_filter:
        # Lọc trạng thái dựa vào property khá khó bằng query ORM thuần vì trang_thai là property động.
        # Ta sẽ lọc bằng Python list comprehension.
        filtered = []
        for sy in schoolyears:
            if sy.trang_thai == status_filter:
                filtered.append(sy)
        schoolyears = filtered
        
    
    paginator = Paginator(schoolyears, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    schoolyears = page_obj
    # inject page_obj into context
    return render(request, 'schoolyear/list.html', {
        'schoolyears': schoolyears,
        'search_query': search_query,
        'status_filter': status_filter
    , 'page_obj': page_obj})

import re

def check_ten_nam_hoc(name):
    match = re.match(r'^(\d{4})-(\d{4})$', name)
    if not match:
        return False
    return int(match.group(2)) == int(match.group(1)) + 1

def validate_school_dates(d):
    try:
        # 7d. Khoảng thời gian năm học không hợp lệ
        if d['NgayBatDau'] >= d['NgayKetThuc']:
            return "Ngày bắt đầu năm học phải nhỏ hơn ngày kết thúc năm học."
            
        # 7e. Thời gian học kỳ không hợp lệ
        if d['HKI_BatDau'] < d['NgayBatDau'] or d['HKI_KetThuc'] > d['NgayKetThuc'] or d['HKI_BatDau'] >= d['HKI_KetThuc']:
            return "Khoảng thời gian học kỳ không hợp lệ."
        if d['HKII_BatDau'] < d['NgayBatDau'] or d['HKII_KetThuc'] > d['NgayKetThuc'] or d['HKII_BatDau'] >= d['HKII_KetThuc']:
            return "Khoảng thời gian học kỳ không hợp lệ."
            
        # 7f. Thứ tự hai học kỳ không hợp lệ
        if d['HKII_BatDau'] <= d['HKI_KetThuc']:
            return "Học kỳ II phải bắt đầu sau khi Học kỳ I kết thúc."
            
        # 7g. Thời gian thi giữa kỳ không hợp lệ
        if d['GiuaKI_BatDau'] < d['HKI_BatDau'] or d['GiuaKI_KetThuc'] > d['HKI_KetThuc'] or d['GiuaKI_BatDau'] > d['GiuaKI_KetThuc']:
            return "Khoảng thời gian thi giữa kỳ không hợp lệ."
        if d['GiuaKII_BatDau'] < d['HKII_BatDau'] or d['GiuaKII_KetThuc'] > d['HKII_KetThuc'] or d['GiuaKII_BatDau'] > d['GiuaKII_KetThuc']:
            return "Khoảng thời gian thi giữa kỳ không hợp lệ."
            
        # 7h. Thời gian thi cuối kỳ không hợp lệ
        if d['CuoiKI_BatDau'] < d['HKI_BatDau'] or d['CuoiKI_KetThuc'] > d['HKI_KetThuc'] or d['CuoiKI_BatDau'] > d['CuoiKI_KetThuc']:
            return "Khoảng thời gian thi cuối kỳ không hợp lệ."
        if d['CuoiKII_BatDau'] < d['HKII_BatDau'] or d['CuoiKII_KetThuc'] > d['HKII_KetThuc'] or d['CuoiKII_BatDau'] > d['CuoiKII_KetThuc']:
            return "Khoảng thời gian thi cuối kỳ không hợp lệ."
            
        # 7i. Thứ tự giữa kỳ và cuối kỳ không hợp lệ
        if d['CuoiKI_BatDau'] < d['GiuaKI_KetThuc']:
            return "Thời gian giữa kỳ và cuối kỳ không hợp lệ."
        if d['CuoiKII_BatDau'] < d['GiuaKII_KetThuc']:
            return "Thời gian giữa kỳ và cuối kỳ không hợp lệ."
            
    except Exception:
        return "Lỗi định dạng ngày tháng."
    return None

@login_required
@admin_required
def schoolyear_create(request):
    if request.method == 'POST':
        TenNamHoc = request.POST.get('TenNamHoc')
        
        # 7b. Tên năm học không hợp lệ
        if not check_ten_nam_hoc(TenNamHoc):
            messages.error(request, 'Tên năm học không hợp lệ.')
            return redirect('schoolyear_create')
            
        # 7c. Trùng tên năm học
        if NamHoc.objects.filter(TenNamHoc=TenNamHoc).exists():
            messages.error(request, 'Năm học đã tồn tại.')
            return redirect('schoolyear_create')
        
        date_fields = ['NgayBatDau', 'NgayKetThuc', 'HKI_BatDau', 'HKI_KetThuc', 'GiuaKI_BatDau', 'GiuaKI_KetThuc', 'CuoiKI_BatDau', 'CuoiKI_KetThuc', 'HKII_BatDau', 'HKII_KetThuc', 'GiuaKII_BatDau', 'GiuaKII_KetThuc', 'CuoiKII_BatDau', 'CuoiKII_KetThuc']
        
        parsed_dates = {}
        for f in date_fields:
            val = request.POST.get(f)
            if not val:
                messages.error(request, 'Vui lòng nhập đầy đủ thông tin năm học.')
                return redirect('schoolyear_create')
            parsed_dates[f] = datetime.strptime(val, '%Y-%m-%d').date()

        err = validate_school_dates(parsed_dates)
        if err:
            messages.error(request, err)
            return redirect('schoolyear_create')
            
        sy = NamHoc(
            TenNamHoc=TenNamHoc, **parsed_dates
        )
        sy.save()
        messages.success(request, 'Thêm năm học thành công.')
        return redirect('schoolyear_list')

    return render(request, 'schoolyear/form.html')

@login_required
@admin_required
def schoolyear_update(request, pk):
    sy = get_object_or_404(NamHoc, pk=pk)
    
    if request.method == 'POST':
        TenNamHoc = request.POST.get('TenNamHoc')
        
        # 7b. Tên năm học không hợp lệ
        if not check_ten_nam_hoc(TenNamHoc):
            messages.error(request, 'Tên năm học không hợp lệ.')
            return redirect('schoolyear_update', pk=pk)
            
        # 7c. Trùng tên năm học
        if NamHoc.objects.filter(TenNamHoc=TenNamHoc).exclude(pk=pk).exists():
            messages.error(request, 'Năm học đã tồn tại.')
            return redirect('schoolyear_update', pk=pk)
        
        date_fields = ['NgayBatDau', 'NgayKetThuc', 'HKI_BatDau', 'HKI_KetThuc', 'GiuaKI_BatDau', 'GiuaKI_KetThuc', 'CuoiKI_BatDau', 'CuoiKI_KetThuc', 'HKII_BatDau', 'HKII_KetThuc', 'GiuaKII_BatDau', 'GiuaKII_KetThuc', 'CuoiKII_BatDau', 'CuoiKII_KetThuc']
        
        parsed_dates = {}
        for f in date_fields:
            val = request.POST.get(f)
            if not val:
                messages.error(request, 'Vui lòng nhập đầy đủ thông tin năm học.')
                return redirect('schoolyear_update', pk=pk)
            parsed_dates[f] = datetime.strptime(val, '%Y-%m-%d').date()
            
        err = validate_school_dates(parsed_dates)
        if err:
            messages.error(request, err)
            return redirect('schoolyear_update', pk=pk)
            
        sy.TenNamHoc = TenNamHoc
        for f, v in parsed_dates.items():
            setattr(sy, f, v)
        sy.save()
        
        messages.success(request, 'Cập nhật năm học thành công.')
        return redirect('schoolyear_list')

    return render(request, 'schoolyear/form.html', {'schoolyear': sy})

@login_required
@admin_required
def schoolyear_delete(request, pk):
    sy = get_object_or_404(NamHoc, pk=pk)
    if request.method == 'POST':
        # Exception 6b. Năm học đã phát sinh dữ liệu
        is_used = False
        if sy.lophoc_set.exists():
            is_used = True
            
        if is_used:
            messages.error(request, 'Không thể xóa năm học đã phát sinh dữ liệu.')
        else:
            sy.delete()
            messages.success(request, 'Xóa năm học thành công.')
            
    return redirect('schoolyear_list')
