from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import GiaoVien
from .decorators import admin_required


@login_required
def account_list(request):
    # Lấy danh sách các giáo viên ĐÃ CÓ tài khoản
    accounts = GiaoVien.objects.filter(user__isnull=False).order_by('-id')
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        accounts = accounts.filter(HoTen__icontains=search_query) | accounts.filter(SDT__icontains=search_query)
        
    if status_filter:
        accounts = accounts.filter(TrangThai=status_filter)
        
    
    paginator = Paginator(accounts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    accounts = page_obj
    # inject page_obj into context
    return render(request, 'account/list.html', {
        'accounts': accounts, 
        'search_query': search_query,
        'status_filter': status_filter
    , 'page_obj': page_obj})

@login_required
@admin_required
def account_create(request):
    # Chỉ lấy những giáo viên CHƯA có tài khoản để cấp
    teachers_without_account = GiaoVien.objects.filter(user__isnull=True)
    
    if request.method == 'POST':
        from django.contrib.auth.models import Group
        sdt = request.POST.get('sdt', '').strip()
        password = request.POST.get('password', 'TH12345!')
        ngaybatdau = request.POST.get('ngaybatdau')
        phanquyen = request.POST.get('phanquyen')
        
        if not sdt or not password or not phanquyen:
            messages.error(request, 'Vui lòng nhập đầy đủ Số điện thoại, Mật khẩu và Phân quyền.')
            return redirect('account_create')
            
        # Check if sdt is valid format: exactly 10 digits, starts with '0'
        if not sdt.isdigit() or len(sdt) != 10 or not sdt.startswith('0'):
            messages.error(request, 'Số điện thoại không hợp lệ hoặc đã được sử dụng')
            return redirect('account_create')
            
        # Check if User already exists
        if User.objects.filter(username=sdt).exists():
            messages.error(request, 'Số điện thoại không hợp lệ hoặc đã được sử dụng')
            return redirect('account_create')
            
        try:
            gv = GiaoVien.objects.get(SDT=sdt)
        except GiaoVien.DoesNotExist:
            messages.error(request, 'Số điện thoại không tồn tại')
            return redirect('account_create')
            
        if gv.user:
            messages.error(request, 'Giáo viên này đã được cấp tài khoản rồi.')
            return redirect('account_create')
            
        # Validate password strength (>=8 chars, alphanumeric)
        if len(password) < 8 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            messages.error(request, 'Mật khẩu không hợp lệ')
            return redirect('account_create')
            
        # Tạo User
        user = User.objects.create_user(username=sdt, password=password)
        
        # Phân quyền
        group, _ = Group.objects.get_or_create(name=phanquyen)
        user.groups.add(group)
        
        # Cập nhật GiaoVien
        gv.user = user
        gv.TrangThai = 'Đang hoạt động'
        if ngaybatdau:
            gv.NgayBatDauChucVu = ngaybatdau
        gv.save()
        
        messages.success(request, f'Cấp tài khoản thành công cho {gv.HoTen}!')
        return redirect('account_list')
        
    return render(request, 'account/form.html', {'teachers': teachers_without_account})

@login_required
@admin_required
def account_update(request, pk):
    gv = get_object_or_404(GiaoVien, pk=pk, user__isnull=False)
    
    if request.method == 'POST':
        from django.contrib.auth.models import Group
        trangthai = request.POST.get('trangthai')
        ngayketthuc = request.POST.get('ngayketthuc')
        phanquyen = request.POST.get('phanquyen')
        reset_pass = request.POST.get('reset_password')
        new_pass = request.POST.get('new_password')
        
        # Đổi phân quyền
        if phanquyen:
            gv.user.groups.clear()
            group, _ = Group.objects.get_or_create(name=phanquyen)
            gv.user.groups.add(group)
            
        ngaybatdau = request.POST.get('ngaybatdau')
        
        # Nếu chưa đăng nhập, cho phép sửa NgayBatDau
        if not gv.user.last_login and ngaybatdau:
            gv.NgayBatDauChucVu = ngaybatdau
            
        # Kiểm tra NgayKetThuc > NgayBatDau
        nbd = ngaybatdau if (not gv.user.last_login and ngaybatdau) else str(gv.NgayBatDauChucVu or '')
        if nbd and ngayketthuc:
            if ngayketthuc <= nbd:
                messages.error(request, 'Ngày kết thúc phải lớn hơn ngày bắt đầu.')
                return redirect('account_update', pk=pk)

        # Đổi trạng thái và ngày kết thúc
        if trangthai in ['Đang hoạt động', 'Dừng hoạt động']:
            gv.TrangThai = trangthai
            if ngayketthuc:
                gv.NgayKetThucChucVu = ngayketthuc
            elif trangthai == 'Đang hoạt động':
                gv.NgayKetThucChucVu = None
            gv.save()
            
            # Nếu dừng hoạt động, disable user đăng nhập
            if trangthai == 'Dừng hoạt động':
                gv.user.is_active = False
            else:
                gv.user.is_active = True
            gv.user.save()
            
        # Đổi mật khẩu
        if reset_pass == 'yes' and new_pass:
            if len(new_pass) < 8 or not any(c.isalpha() for c in new_pass) or not any(c.isdigit() for c in new_pass):
                messages.error(request, 'Mật khẩu không hợp lệ')
                return redirect('account_update', pk=pk)
                
            gv.user.set_password(new_pass)
            gv.user.save()
            messages.success(request, 'Đã cấp lại mật khẩu thành công!')
            
        messages.success(request, 'Cập nhật tài khoản thành công!')
        return redirect('account_list')
        
    return render(request, 'account/form_update.html', {'account': gv})

@login_required
@admin_required
def account_delete(request, pk):
    gv = get_object_or_404(GiaoVien, pk=pk, user__isnull=False)
    if request.method == 'POST':
        if hasattr(request.user, 'giaovien') and request.user.giaovien == gv:
            messages.error(request, 'Không thể xóa tài khoản của chính mình.')
            return redirect('account_list')
            
        # Exception 5a: Tài khoản đã sử dụng cho các phiên làm việc
        is_used = (
            gv.lophoc_set.exists() or 
            gv.phanconggiangday_set.exists() or
            gv.dethi_tao.exists() or
            gv.dethi_duyet.exists() or
            gv.matran_set.exists() or
            gv.giam_thi_1_set.exists() or
            gv.giam_thi_2_set.exists()
        )
            
        if is_used:
            messages.error(request, 'Không thể xóa do đã sử dụng cho các phiên làm việc')
            return redirect('account_list')
            
        # Theo business rule, tài khoản xóa khỏi danh sách, giáo viên không thể đăng nhập
        user_to_delete = gv.user
        gv.user = None
        gv.TrangThai = 'Chưa cấp tài khoản'
        gv.save()
        user_to_delete.delete()
        
        messages.success(request, 'Xóa tài khoản thành công!')
    return redirect('account_list')
