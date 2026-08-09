from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import GiaoVien, MonHoc, Khoi
import pandas as pd
import uuid
from datetime import datetime
from .decorators import admin_required


@login_required
def teacher_list(request):
    teachers = GiaoVien.objects.all().prefetch_related('MonGiangDay', 'KhoiPhuTrach').order_by('-id')
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        teachers = teachers.filter(HoTen__icontains=search_query) | teachers.filter(SDT__icontains=search_query)
        
    if status_filter:
        teachers = teachers.filter(TrangThai=status_filter)
        
    
    paginator = Paginator(teachers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    teachers = page_obj
    # inject page_obj into context
    return render(request, 'teacher/list.html', {
        'teachers': teachers, 
        'search_query': search_query,
        'status_filter': status_filter
    , 'page_obj': page_obj})

@login_required
@admin_required
def teacher_create(request):
    mon_hocs = MonHoc.objects.all()
    khoi_list = Khoi.objects.all()
    if request.method == 'POST':
        hoten = request.POST.get('hoten')
        sdt = request.POST.get('sdt')
        email = request.POST.get('email')
        gioitinh = request.POST.get('gioitinh')
        ngaysinh = request.POST.get('ngaysinh')
        chucvu = request.POST.get('chucvu')
        ngaybatdau = request.POST.get('ngaybatdau')
        mon_giang_day = request.POST.getlist('mongiangday')
        khoi_phu_trach = request.POST.getlist('khoiphutach')
        
        if not hoten or not sdt or not gioitinh or not ngaysinh or not email or not chucvu or not ngaybatdau:
            messages.error(request, 'Vui lòng nhập đầy đủ các thông tin bắt buộc.')
            return redirect('teacher_create')
            
        if chucvu != 'Admin/Giáo vụ' and not mon_giang_day:
            messages.error(request, 'Vui lòng chọn Môn giảng dạy.')
            return redirect('teacher_create')

        if len(sdt) != 10 or not sdt.startswith('0'):
            messages.error(request, 'Số điện thoại phải gồm 10 chữ số và bắt đầu bằng số 0.')
            return redirect('teacher_create')
            
        if GiaoVien.objects.filter(SDT=sdt).exists() or GiaoVien.objects.filter(Email=email).exists():
            messages.error(request, 'Số điện thoại hoặc Email đã tồn tại!')
            return redirect('teacher_create')
            
        gv = GiaoVien.objects.create(
            HoTen=hoten,
            SDT=sdt,
            Email=email,
            GioiTinh=gioitinh,
            NgaySinh=ngaysinh,
            ChucVu=chucvu,
            NgayBatDauChucVu=ngaybatdau,
            TrangThai='Chưa cấp tài khoản'
        )
        for m in mon_giang_day:
            gv.MonGiangDay.add(m)
        if chucvu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
            for k in khoi_phu_trach:
                gv.KhoiPhuTrach.add(k)
            
        messages.success(request, 'Thêm giáo viên thành công!')
        return redirect('teacher_list')
        
    return render(request, 'teacher/form.html', {'mon_hocs': mon_hocs, 'khoi_list': khoi_list})

@login_required
@admin_required
def teacher_update(request, pk):
    teacher = get_object_or_404(GiaoVien, pk=pk)
    mon_hocs = MonHoc.objects.all()
    khoi_list = Khoi.objects.all()
    
    if request.method == 'POST':
        hoten = request.POST.get('hoten')
        sdt = request.POST.get('sdt')
        email = request.POST.get('email')
        gioitinh = request.POST.get('gioitinh')
        ngaysinh = request.POST.get('ngaysinh')
        chucvu = request.POST.get('chucvu')
        ngaybatdau = request.POST.get('ngaybatdau')
        mon_giang_day = request.POST.getlist('mongiangday')
        khoi_phu_trach = request.POST.getlist('khoiphutach')
        
        if not hoten or not sdt or not gioitinh or not ngaysinh or not email or not chucvu or not ngaybatdau:
            messages.error(request, 'Vui lòng nhập đầy đủ các thông tin bắt buộc.')
            return redirect('teacher_update', pk=pk)
            
        if chucvu != 'Admin/Giáo vụ' and not mon_giang_day:
            messages.error(request, 'Vui lòng chọn Môn giảng dạy.')
            return redirect('teacher_update', pk=pk)

        # Check trùng SDT / Email (ngoại trừ chính nó)
        if GiaoVien.objects.filter(SDT=sdt).exclude(pk=pk).exists():
            messages.error(request, 'Số điện thoại đã tồn tại ở hồ sơ khác!')
            return redirect('teacher_update', pk=pk)
            
        if GiaoVien.objects.filter(Email=email).exclude(pk=pk).exists():
            messages.error(request, 'Email đã tồn tại ở hồ sơ khác!')
            return redirect('teacher_update', pk=pk)
            
        teacher.HoTen = hoten
        teacher.SDT = sdt
        teacher.Email = email
        teacher.GioiTinh = gioitinh
        teacher.NgaySinh = ngaysinh
        teacher.ChucVu = chucvu
        teacher.NgayBatDauChucVu = ngaybatdau
        teacher.save()
        
        # Update ManyToMany môn giảng dạy
        teacher.MonGiangDay.clear()
        for m in mon_giang_day:
            teacher.MonGiangDay.add(m)
        
        # Update khối phụ trách (chỉ áp dụng cho Tổ trưởng/Tổ phó)
        teacher.KhoiPhuTrach.clear()
        if chucvu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
            for k in khoi_phu_trach:
                teacher.KhoiPhuTrach.add(k)
            
        messages.success(request, 'Cập nhật hồ sơ giáo viên thành công!')
        return redirect('teacher_list')
        
    return render(request, 'teacher/form.html', {'mon_hocs': mon_hocs, 'khoi_list': khoi_list, 'teacher': teacher})

@login_required
@admin_required
def teacher_delete(request, pk):
    teacher = get_object_or_404(GiaoVien, pk=pk)
    if request.method == 'POST':
        # Không cho phép tự xóa chính mình
        if hasattr(request.user, 'giaovien') and request.user.giaovien == teacher:
            messages.error(request, 'Hệ thống từ chối: Bạn không thể tự xóa tài khoản đang đăng nhập của chính mình!')
            return redirect('teacher_list')
            
        # Exception 5a: Hồ sơ đã sử dụng cho các phiên làm việc
        is_used = False
        if teacher.lophoc_set.exists():
            is_used = True
        if teacher.phanconggiangday_set.exists():
            is_used = True
            
        if is_used:
            messages.error(request, 'Không thể xóa do đã sử dụng cho các phiên làm việc')
        else:
            teacher.delete()
            messages.success(request, 'Xóa tài khoản thành công!')
            
    return redirect('teacher_list')

@login_required
@admin_required
def teacher_import(request):
    if request.method == 'POST':
        if 'file' in request.FILES:
            excel_file = request.FILES['file']
            try:
                df = pd.read_excel(excel_file)
                required_cols = ['HoTen', 'GioiTinh', 'NgaySinh', 'Email', 'SDT', 'ChucVu', 'NgayBatDau']
                if not all(col in df.columns for col in required_cols):
                    messages.error(request, f'File không đúng định dạng. Yêu cầu các cột: {", ".join(required_cols)}')
                    return redirect('teacher_import')
                
                preview_data = []
                session_key = f'import_teachers_{uuid.uuid4()}'
                valid_count = 0
                
                for index, row in df.iterrows():
                    sdt = str(row['SDT']).strip()
                    if sdt.endswith('.0'): sdt = sdt[:-2]
                    
                    email = str(row['Email']).strip()
                    
                    errors = []
                    if GiaoVien.objects.filter(SDT=sdt).exists():
                        errors.append("SĐT đã tồn tại")
                    if GiaoVien.objects.filter(Email=email).exists():
                        errors.append("Email đã tồn tại")
                        
                    is_valid = len(errors) == 0
                    if is_valid: valid_count += 1
                    
                    ngaysinh = row['NgaySinh']
                    if hasattr(ngaysinh, 'strftime'): ngaysinh = ngaysinh.strftime('%Y-%m-%d')
                    else: ngaysinh = str(ngaysinh)
                        
                    ngaybatdau = row['NgayBatDau']
                    if hasattr(ngaybatdau, 'strftime'): ngaybatdau = ngaybatdau.strftime('%Y-%m-%d')
                    else: ngaybatdau = str(ngaybatdau)
                        
                    preview_data.append({
                        'hoten': str(row['HoTen']),
                        'gioitinh': str(row['GioiTinh']),
                        'ngaysinh': ngaysinh,
                        'email': email,
                        'sdt': sdt,
                        'chucvu': str(row['ChucVu']),
                        'ngaybatdau': ngaybatdau,
                        'is_valid': is_valid,
                        'errors': ", ".join(errors)
                    })
                
                request.session[session_key] = preview_data
                return render(request, 'teacher/import_preview.html', {
                    'data': preview_data,
                    'session_key': session_key,
                    'valid_count': valid_count
                })
                
            except Exception as e:
                messages.error(request, f'Lỗi đọc file: {str(e)}')
                return redirect('teacher_import')
                
        elif 'confirm_import' in request.POST:
            session_key = request.POST.get('session_key')
            data = request.session.get(session_key)
            if not data:
                messages.error(request, 'Phiên import đã hết hạn hoặc không tồn tại.')
                return redirect('teacher_import')
                
            count = 0
            for item in data:
                if item['is_valid']:
                    GiaoVien.objects.create(
                        HoTen=item['hoten'],
                        GioiTinh=item['gioitinh'],
                        NgaySinh=item['ngaysinh'],
                        Email=item['email'],
                        SDT=item['sdt'],
                        ChucVu=item['chucvu'],
                        NgayBatDauChucVu=item['ngaybatdau']
                    )
                    count += 1
                    
            del request.session[session_key]
            messages.success(request, f'Import thành công {count} giáo viên.')
            return redirect('teacher_list')
            
    return render(request, 'teacher/import.html')
