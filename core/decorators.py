from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            giaovien = getattr(request.user, 'giaovien', None)
            if not giaovien:
                messages.error(request, 'Bạn không có quyền thực hiện chức năng này.')
                return redirect('dashboard')
                
            if giaovien.ChucVu in allowed_roles:
                return view_func(request, *args, **kwargs)
                
            messages.error(request, 'Bạn không có quyền thực hiện chức năng này.')
            return redirect('dashboard')
            
        return _wrapped_view
    return decorator

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
            
        giaovien = getattr(request.user, 'giaovien', None)
        if giaovien and giaovien.ChucVu == 'Nhân viên văn thư':
            return view_func(request, *args, **kwargs)
            
        messages.error(request, 'Chỉ Admin/Giáo vụ mới có quyền thực hiện chức năng này.')
        # fallback redirect
        return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
        
    return _wrapped_view

def khao_thi_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
            
        giaovien = getattr(request.user, 'giaovien', None)
        if giaovien and giaovien.ChucVu != 'Nhân viên văn thư':
            return view_func(request, *args, **kwargs)
            
        messages.error(request, 'Admin/Giáo vụ không có quyền truy cập chức năng Khảo thí.')
        return redirect('dashboard')
        
    return _wrapped_view
