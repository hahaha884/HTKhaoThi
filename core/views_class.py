from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import LopHoc, NamHoc, Khoi, GiaoVien
from .decorators import admin_required


@login_required
def class_list(request):
    classes = LopHoc.objects.all().order_by('-id')
    
    # 12.4 Tìm kiếm lớp
    search_query = request.GET.get('search', '')
    namhoc_filter = request.GET.get('namhoc', '')
    khoi_filter = request.GET.get('khoi', '')
    
    if search_query:
        classes = classes.filter(TenLop__icontains=search_query)
        
    if namhoc_filter:
        classes = classes.filter(MaNamHoc_id=namhoc_filter)
        
    if khoi_filter:
        classes = classes.filter(MaKhoi_id=khoi_filter)
        
    namhocs = NamHoc.objects.all()
    khois = Khoi.objects.all()
        
    
    paginator = Paginator(classes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    classes = page_obj
    # inject page_obj into context
    return render(request, 'class/list.html', {
        'classes': classes,
        'search_query': search_query,
        'namhoc_filter': namhoc_filter,
        'khoi_filter': khoi_filter,
        'namhocs': namhocs,
        'khois': khois
    , 'page_obj': page_obj})

@login_required
@admin_required
def class_create(request):
    namhocs = NamHoc.objects.all()
    khois = Khoi.objects.all()
    giaoviens = GiaoVien.objects.filter(ChucVu='Giáo viên chủ nhiệm')
    
    for gv in giaoviens:
        gv.assigned_namhocs = list(LopHoc.objects.filter(GVCN=gv).values_list('MaNamHoc_id', flat=True))
    
    if request.method == 'POST':
        ten_lop = request.POST.get('TenLop')
        ma_khoi_id = request.POST.get('MaKhoi')
        ma_nam_hoc_id = request.POST.get('MaNamHoc')
        si_so = request.POST.get('SiSoToiDa')
        gvcn_id = request.POST.get('GVCN')
        
        if not ten_lop or not ma_khoi_id or not ma_nam_hoc_id or not si_so:
            messages.error(request, 'Vui lòng nhập đầy đủ các trường bắt buộc.')
            return redirect('class_create')
            
        # Format TenLop (VD: Nhập A1 -> 1A1)
        khoi = Khoi.objects.get(pk=ma_khoi_id)
        prefix = khoi.TenKhoi.replace('Khối ', '').strip()
        if not ten_lop.startswith(prefix):
            ten_lop = f"{prefix}{ten_lop}"
            
        # Exception 5b: Tên lớp trong cùng khối cùng năm trùng nhau
        if LopHoc.objects.filter(TenLop=ten_lop, MaKhoi_id=ma_khoi_id, MaNamHoc_id=ma_nam_hoc_id).exists():
            messages.error(request, 'Thông tin trùng lặp')
            return redirect('class_create')
            
        # Exception 5c: GVCN bị trùng giữa các lớp trong cùng 1 năm
        if gvcn_id:
            if LopHoc.objects.filter(GVCN_id=gvcn_id, MaNamHoc_id=ma_nam_hoc_id).exists():
                messages.error(request, 'Giáo viên này đã có lớp chủ nhiệm')
                return redirect('class_create')
                
        lop = LopHoc(
            TenLop=ten_lop,
            MaKhoi_id=ma_khoi_id,
            MaNamHoc_id=ma_nam_hoc_id,
            SiSoToiDa=si_so,
            GVCN_id=gvcn_id if gvcn_id else None
        )
        lop.save()
        messages.success(request, 'Thêm lớp học thành công.')
        return redirect('class_list')
        
    return render(request, 'class/form.html', {
        'namhocs': namhocs,
        'khois': khois,
        'giaoviens': giaoviens
    })

@login_required
@admin_required
def class_update(request, pk):
    lop = get_object_or_404(LopHoc, pk=pk)
    namhocs = NamHoc.objects.all()
    khois = Khoi.objects.all()
    giaoviens = GiaoVien.objects.filter(ChucVu='Giáo viên chủ nhiệm')
    
    # Loại trừ lớp hiện tại ra khỏi danh sách đã phân công
    for gv in giaoviens:
        gv.assigned_namhocs = list(LopHoc.objects.filter(GVCN=gv).exclude(pk=pk).values_list('MaNamHoc_id', flat=True))
    
    if request.method == 'POST':
        ten_lop = request.POST.get('TenLop')
        ma_khoi_id = request.POST.get('MaKhoi')
        ma_nam_hoc_id = request.POST.get('MaNamHoc')
        si_so = request.POST.get('SiSoToiDa')
        gvcn_id = request.POST.get('GVCN')
        
        if not ten_lop or not ma_khoi_id or not ma_nam_hoc_id or not si_so:
            messages.error(request, 'Vui lòng nhập đầy đủ các trường bắt buộc.')
            return redirect('class_update', pk=pk)
            
        # Format TenLop
        khoi = Khoi.objects.get(pk=ma_khoi_id)
        prefix = khoi.TenKhoi.replace('Khối ', '').strip()
        if not ten_lop.startswith(prefix):
            ten_lop = f"{prefix}{ten_lop}"
            
        # Exception 6b: Tên lớp trong cùng khối cùng năm đã tồn tại
        if LopHoc.objects.filter(TenLop=ten_lop, MaKhoi_id=ma_khoi_id, MaNamHoc_id=ma_nam_hoc_id).exclude(pk=pk).exists():
            messages.error(request, 'Thông tin đã tồn tại')
            return redirect('class_update', pk=pk)
            
        # Exception 6c: GVCN bị trùng giữa các lớp trong cùng 1 năm
        if gvcn_id:
            if LopHoc.objects.filter(GVCN_id=gvcn_id, MaNamHoc_id=ma_nam_hoc_id).exclude(pk=pk).exists():
                messages.error(request, 'Giáo viên này đã có lớp chủ nhiệm')
                return redirect('class_update', pk=pk)
                
        lop.TenLop = ten_lop
        lop.MaKhoi_id = ma_khoi_id
        lop.MaNamHoc_id = ma_nam_hoc_id
        lop.SiSoToiDa = si_so
        lop.GVCN_id = gvcn_id if gvcn_id else None
        lop.save()
        
        messages.success(request, 'Cập nhật lớp học thành công.')
        return redirect('class_list')
        
    return render(request, 'class/form.html', {
        'lop': lop,
        'namhocs': namhocs,
        'khois': khois,
        'giaoviens': giaoviens
    })

@login_required
@admin_required
def class_delete(request, pk):
    lop = get_object_or_404(LopHoc, pk=pk)
    if request.method == 'POST':
        # Exception 5a: Hồ sơ đã sử dụng cho các phiên làm việc
        is_used = False
        if hasattr(lop, 'phanconggiangday_set') and lop.phanconggiangday_set.exists():
            is_used = True
            
        if is_used:
            messages.error(request, 'Không thể xóa do đã sử dụng cho các phiên làm việc')
        else:
            lop.delete()
            messages.success(request, 'Xóa lớp học thành công.')
    return redirect('class_list')
