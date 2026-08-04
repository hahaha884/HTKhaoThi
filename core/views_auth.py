from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.core.cache import cache

def login_view(request):
    if request.method == 'POST':
        sdt = request.POST.get('sdt', '').strip()
        password = request.POST.get('password')
        
        if not sdt or not password:
            messages.error(request, "Vui lòng nhập đầy đủ số điện thoại và mật khẩu.")
            return render(request, 'auth/login.html')
            
        # Kiểm tra tài khoản có đang bị khóa hay không
        lock_key = f'lockout_{sdt}'
        attempts_key = f'attempts_{sdt}'
        
        if cache.get(lock_key):
            messages.error(request, "Tài khoản đã bị tạm khóa trong 5 phút do đăng nhập sai quá 05 lần. Vui lòng thử lại sau hoặc liên hệ Văn thư nếu cần hỗ trợ.")
            return render(request, 'auth/login.html')
            
        user = authenticate(request, username=sdt, password=password)
        
        if user is not None:
            # Đăng nhập thành công, xóa số lần đăng nhập sai
            cache.delete(attempts_key)
            is_first_login = (user.last_login is None)
            login(request, user)
            if is_first_login:
                request.session['force_password_change'] = True
                return redirect('change_password_first_login')
            return redirect('/') # Chuyển tới trang chủ
        else:
            # Đăng nhập thất bại
            attempts = cache.get(attempts_key, 0) + 1
            cache.set(attempts_key, attempts, 300) # Hết hạn sau 5 phút
            
            if attempts >= 5:
                cache.set(lock_key, True, 300) # Khóa 5 phút
                messages.error(request, "Tài khoản đã bị tạm khóa trong 5 phút do đăng nhập sai quá 05 lần. Vui lòng thử lại sau hoặc liên hệ Văn thư nếu cần hỗ trợ.")
            else:
                messages.error(request, "Tên đăng nhập hoặc mật khẩu không hợp lệ. Vui lòng nhập lại.")
            return render(request, 'auth/login.html')
            
    return render(request, 'auth/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def tao_to2(request):
    from django.contrib.auth.models import User
    from core.models import GiaoVien, ToChuyenMon
    
    user, _ = User.objects.get_or_create(username='0123456782', defaults={'first_name': 'Tổ trưởng', 'last_name': 'Tổ 2'})
    user.set_password('123456')
    user.save()
    
    to_2, _ = ToChuyenMon.objects.get_or_create(TenTo='Tổ 2')
    
    gv, _ = GiaoVien.objects.get_or_create(user=user, defaults={
        'HoTen': 'Tổ trưởng Tổ 2', 
        'ChucVu': 'Tổ trưởng chuyên môn', 
        'ToChuyenMon': to_2, 
        'SoDienThoai': '0123456782', 
        'Email': 'totruong2@example.com', 
        'TrangThai': 'Đang làm việc'
    })
    
    return render(request, 'auth/login.html', {'messages': [{'tags': 'success', 'message': 'Đã tạo tài khoản Tổ trưởng Tổ 2 thành công! (SDT: 0123456782 / Pass: 123456)'}]})

from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash

@login_required
def change_password_first_login(request):
    if not request.session.get('force_password_change'):
        return redirect('/')
        
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not old_password or not new_password or not confirm_password:
            messages.error(request, "Vui lòng nhập đầy đủ thông tin.")
            return render(request, 'auth/change_password.html')
            
        if new_password != confirm_password:
            messages.error(request, "Mật khẩu xác nhận không khớp.")
            return render(request, 'auth/change_password.html')
            
        if not request.user.check_password(old_password):
            messages.error(request, "Mật khẩu hiện tại không đúng.")
            return render(request, 'auth/change_password.html')
            
        # Update password
        request.user.set_password(new_password)
        request.user.save()
        
        # Keep user logged in after password change
        update_session_auth_hash(request, request.user)
        
        # Clear the flag
        if 'force_password_change' in request.session:
            del request.session['force_password_change']
            
        messages.success(request, "Đổi mật khẩu thành công. Chào mừng bạn đến với hệ thống!")
        return redirect('/')
        
    return render(request, 'auth/change_password.html')
