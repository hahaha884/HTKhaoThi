from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import MonHoc, Khoi
from .decorators import admin_required


@login_required
def subject_list(request):
    subjects = MonHoc.objects.all().order_by('-id')
    
    # 15.2 Tìm kiếm môn học
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        subjects = subjects.filter(TenMon__icontains=search_query)
        
    if status_filter:
        subjects = subjects.filter(TrangThai=status_filter)
        
    
    paginator = Paginator(subjects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    subjects = page_obj
    # inject page_obj into context
    return render(request, 'subject/list.html', {
        'subjects': subjects,
        'search_query': search_query,
        'status_filter': status_filter
    , 'page_obj': page_obj})

@login_required
@admin_required
def subject_create(request):
    khoi_list = Khoi.objects.all()
    if request.method == 'POST':
        ten_mon = request.POST.get('TenMon')
        mo_ta = request.POST.get('MoTa')
        trang_thai = request.POST.get('TrangThai')
        khoi_ap_dung = request.POST.getlist('KhoiApDung')
        
        # 15.1 Thiếu trường bắt buộc
        if not ten_mon or not trang_thai:
            messages.error(request, 'Vui lòng nhập đầy đủ các trường bắt buộc.')
            return redirect('subject_create')
            
        # 15.1 Tên môn tồn tại
        if MonHoc.objects.filter(TenMon=ten_mon).exists():
            messages.error(request, 'Thông tin tồn tại')
            return redirect('subject_create')
            
        subject = MonHoc(TenMon=ten_mon, MoTa=mo_ta, TrangThai=trang_thai)
        subject.save()
        if khoi_ap_dung:
            subject.KhoiApDung.set(khoi_ap_dung)
            
        messages.success(request, 'Thêm môn học thành công.')
        return redirect('subject_list')
        
    return render(request, 'subject/form.html', {'khoi_list': khoi_list})

@login_required
@admin_required
def subject_update(request, pk):
    subject = get_object_or_404(MonHoc, pk=pk)
    khoi_list = Khoi.objects.all()
    
    if request.method == 'POST':
        ten_mon = request.POST.get('TenMon')
        mo_ta = request.POST.get('MoTa')
        trang_thai = request.POST.get('TrangThai')
        khoi_ap_dung = request.POST.getlist('KhoiApDung')
        
        # 15.3 Thiếu trường bắt buộc
        if not ten_mon or not trang_thai:
            messages.error(request, 'Vui lòng nhập đầy đủ các trường bắt buộc.')
            return redirect('subject_update', pk=pk)
            
        # 15.3 Tên môn tồn tại
        if MonHoc.objects.filter(TenMon=ten_mon).exclude(pk=pk).exists():
            messages.error(request, 'Thông tin tồn tại')
            return redirect('subject_update', pk=pk)
            
        subject.TenMon = ten_mon
        subject.MoTa = mo_ta
        subject.TrangThai = trang_thai
        subject.save()
        subject.KhoiApDung.set(khoi_ap_dung)
        
        messages.success(request, 'Cập nhật môn học thành công.')
        return redirect('subject_list')
        
    return render(request, 'subject/form.html', {'subject': subject, 'khoi_list': khoi_list})

@login_required
@admin_required
def subject_delete(request, pk):
    subject = get_object_or_404(MonHoc, pk=pk)
    if request.method == 'POST':
        # UC 15.4 - BR1: Kiểm tra ràng buộc trước khi xóa
        is_used = False
        
        # Kiểm tra đã phân công giảng dạy cho giáo viên chưa
        if subject.giaovien_set.exists():
            is_used = True
        
        # Kiểm tra đã có ma trận sử dụng môn này chưa
        if not is_used and subject.matran_set.exists():
            is_used = True
        
        # Kiểm tra đã có câu hỏi trong ngân hàng thuộc môn này chưa
        if not is_used:
            from question_bank.models import CauHoi
            if CauHoi.objects.filter(MonHoc=subject).exists():
                is_used = True
            
        if is_used:
            # UC 15.4 - 5a: Hiển thị lỗi nếu đã sử dụng
            messages.error(request, 'Không thể xóa do đã sử dụng cho các phiên làm việc')
        else:
            subject.delete()
            messages.success(request, 'Xóa môn học thành công.')
    return redirect('subject_list')
