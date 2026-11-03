from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.decorators import khao_thi_required
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta, date
from .models import LichThi
from exam.models import DeThi
from core.models import NamHoc, Khoi, MonHoc, GiaoVien


@login_required
@khao_thi_required
def schedule_list(request):
    """
    UC 6.4: Danh sách và tìm kiếm lịch thi
    Tất cả role đều có thể xem
    """
    lich_thi_list = LichThi.objects.all().select_related(
        'NamHoc', 'Khoi', 'MonHoc', 'DeThi', 'NguoiTao'
    ).order_by('NgayThi', 'GioBatDau')
    
    # Tìm kiếm và lọc (UC 6.4)
    tu_khoa = request.GET.get('q', '')
    if tu_khoa:
        lich_thi_list = lich_thi_list.filter(
            Q(MonHoc__TenMon__icontains=tu_khoa) |
            Q(Khoi__TenKhoi__icontains=tu_khoa) |
            Q(GhiChu__icontains=tu_khoa)
        )
    
    # Bộ lọc
    khoi_id = request.GET.get('khoi')
    if khoi_id:
        lich_thi_list = lich_thi_list.filter(Khoi_id=khoi_id)
    
    mon_id = request.GET.get('mon')
    if mon_id:
        lich_thi_list = lich_thi_list.filter(MonHoc_id=mon_id)
    
    ca_thi = request.GET.get('ca')
    if ca_thi:
        lich_thi_list = lich_thi_list.filter(CaThi=ca_thi)
        
    hoc_ky = request.GET.get('hoc_ky')
    if hoc_ky:
        lich_thi_list = lich_thi_list.filter(HocKy=hoc_ky)
        
    ky_thi = request.GET.get('ky_thi')
    if ky_thi:
        lich_thi_list = lich_thi_list.filter(KyThi=ky_thi)
    
    ngay_thi = request.GET.get('ngay')
    if ngay_thi:
        try:
            ngay_obj = datetime.strptime(ngay_thi, '%Y-%m-%d').date()
            lich_thi_list = lich_thi_list.filter(NgayThi=ngay_obj)
        except:
            pass
    
    nam_hoc_id = request.GET.get('nam_hoc')
    if nam_hoc_id:
        lich_thi_list = lich_thi_list.filter(NamHoc_id=nam_hoc_id)
    
    # Kiểm tra quyền
    gv = getattr(request.user, 'giaovien', None)
    is_bgh = gv and gv.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']
    
    from django.core.paginator import Paginator
    paginator = Paginator(lich_thi_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    lich_thi_list = page_obj

    context = {
        'lich_thi_list': lich_thi_list,
        'page_obj': page_obj,
        'tu_khoa': tu_khoa,
        'khoi_list': Khoi.objects.all(),
        'mon_list': MonHoc.objects.filter(TrangThai__in=['Đang hoạt động', 'Đang áp dụng']),
        'nam_hoc_list': NamHoc.objects.all(),
        'is_bgh': is_bgh,
    }
    return render(request, 'schedule/list.html', context)


@login_required
@khao_thi_required
def schedule_create_step1(request):
    """
    UC 6.1: Tạo lịch thi - Bước 1 (Nhập thông tin ca thi)
    Chỉ BGH được tạo
    """
    gv = getattr(request.user, 'giaovien', None)
    if not gv or gv.ChucVu not in ['Hiệu trưởng', 'Phó hiệu trưởng']:
        messages.error(request, "Chỉ Ban Giám Hiệu mới có quyền tạo lịch thi.")
        return redirect('schedule_list')
    
    def _render_step1_err(req, field_errors, pd=None):
        """Helper: render lại Bước 1 với lỗi field, giữ dữ liệu đã nhập."""
        from schedule.models import NamHoc, Khoi
        from subject.models import MonHoc
        return render(req, 'schedule/create_step1.html', {
            'step1_data': pd or {},
            'field_errors': field_errors,
            'nam_hoc_list': NamHoc.objects.all(),
            'khoi_list': Khoi.objects.all(),
            'mon_list': MonHoc.objects.filter(TrangThai='Đang hoạt động'),
        })

    if request.method == 'POST':
        nam_hoc_id = request.POST.get('nam_hoc')
        khoi_id = request.POST.get('khoi')
        mon_id = request.POST.get('mon')
        hoc_ky = request.POST.get('hoc_ky')
        ky_thi = request.POST.get('ky_thi')
        ca_thi = request.POST.get('ca_thi')
        ngay_thi_str = request.POST.get('ngay_thi')
        gio_bat_dau_str = request.POST.get('gio_bat_dau')
        gio_ket_thuc_str = request.POST.get('gio_ket_thuc')
        ghi_chu = request.POST.get('ghi_chu', '')

        # Giữ lại giá trị form để hiển thị lại khi có lỗi
        post_data = {
            'nam_hoc_id': nam_hoc_id,
            'khoi_id': khoi_id,
            'mon_id': mon_id,
            'hoc_ky': hoc_ky,
            'ky_thi': ky_thi,
            'ca_thi': ca_thi,
            'ngay_thi': ngay_thi_str,
            'gio_bat_dau': gio_bat_dau_str,
            'gio_ket_thuc': gio_ket_thuc_str,
            'ghi_chu': ghi_chu,
        }

        field_errors = {}

        # Exception 6a1: Thiếu trường bắt buộc
        missing = []
        if not nam_hoc_id: missing.append('nam_hoc')
        if not hoc_ky: missing.append('hoc_ky')
        if not ky_thi: missing.append('ky_thi')
        if not khoi_id: missing.append('khoi')
        if not mon_id: missing.append('mon')
        if not ca_thi: missing.append('ca_thi')
        if not ngay_thi_str: missing.append('ngay_thi')
        if not gio_bat_dau_str: missing.append('gio_bat_dau')
        if not gio_ket_thuc_str: missing.append('gio_ket_thuc')
        if missing:
            for f in missing:
                field_errors[f] = "Trường này là bắt buộc."
            return _render_step1_err(request, field_errors, post_data)

        try:
            ngay_thi = datetime.strptime(ngay_thi_str, '%Y-%m-%d').date()
            gio_bat_dau = datetime.strptime(gio_bat_dau_str, '%H:%M').time()
            gio_ket_thuc = datetime.strptime(gio_ket_thuc_str, '%H:%M').time()
        except Exception:
            field_errors['ngay_thi'] = "Định dạng ngày không hợp lệ."
            return _render_step1_err(request, field_errors, post_data)

        # Exception 6b: Giờ kết thúc < Giờ bắt đầu
        if gio_ket_thuc <= gio_bat_dau:
            field_errors['gio_ket_thuc'] = "Giờ kết thúc phải lớn hơn giờ bắt đầu."
            return _render_step1_err(request, field_errors, post_data)

        # Exception 6b2: Ràng buộc giờ theo ca thi
        if ca_thi == 'Buổi sáng' and gio_bat_dau.hour >= 12:
            field_errors['gio_bat_dau'] = "Buổi sáng phải có giờ bắt đầu trước 12:00 trưa."
            return _render_step1_err(request, field_errors, post_data)
        if ca_thi == 'Buổi chiều' and gio_bat_dau.hour < 12:
            field_errors['gio_bat_dau'] = "Buổi chiều phải có giờ bắt đầu từ 12:00 trưa trở đi."
            return _render_step1_err(request, field_errors, post_data)

        # Exception 6c: Kiểm tra ngày thi nằm trong khoảng thời gian của kỳ thi đã chọn
        if nam_hoc_id:
            nam_hoc = NamHoc.objects.filter(id=nam_hoc_id).first()
            if nam_hoc:
                hop_le = True
                khoang_thoi_gian = ""

                if hoc_ky == 'Học kỳ 1' and ky_thi == 'Giữa kỳ':
                    if not (nam_hoc.GiuaKI_BatDau and nam_hoc.GiuaKI_KetThuc) or not (nam_hoc.GiuaKI_BatDau <= ngay_thi <= nam_hoc.GiuaKI_KetThuc):
                        hop_le = False
                        khoang_thoi_gian = f"{nam_hoc.GiuaKI_BatDau.strftime('%d/%m/%Y')} – {nam_hoc.GiuaKI_KetThuc.strftime('%d/%m/%Y')}" if nam_hoc.GiuaKI_BatDau else "Chưa cấu hình"
                elif hoc_ky == 'Học kỳ 1' and ky_thi == 'Cuối kỳ':
                    if not (nam_hoc.CuoiKI_BatDau and nam_hoc.CuoiKI_KetThuc) or not (nam_hoc.CuoiKI_BatDau <= ngay_thi <= nam_hoc.CuoiKI_KetThuc):
                        hop_le = False
                        khoang_thoi_gian = f"{nam_hoc.CuoiKI_BatDau.strftime('%d/%m/%Y')} – {nam_hoc.CuoiKI_KetThuc.strftime('%d/%m/%Y')}" if nam_hoc.CuoiKI_BatDau else "Chưa cấu hình"
                elif hoc_ky == 'Học kỳ 2' and ky_thi == 'Giữa kỳ':
                    if not (nam_hoc.GiuaKII_BatDau and nam_hoc.GiuaKII_KetThuc) or not (nam_hoc.GiuaKII_BatDau <= ngay_thi <= nam_hoc.GiuaKII_KetThuc):
                        hop_le = False
                        khoang_thoi_gian = f"{nam_hoc.GiuaKII_BatDau.strftime('%d/%m/%Y')} – {nam_hoc.GiuaKII_KetThuc.strftime('%d/%m/%Y')}" if nam_hoc.GiuaKII_BatDau else "Chưa cấu hình"
                elif hoc_ky == 'Học kỳ 2' and ky_thi == 'Cuối kỳ':
                    if not (nam_hoc.CuoiKII_BatDau and nam_hoc.CuoiKII_KetThuc) or not (nam_hoc.CuoiKII_BatDau <= ngay_thi <= nam_hoc.CuoiKII_KetThuc):
                        hop_le = False
                        khoang_thoi_gian = f"{nam_hoc.CuoiKII_BatDau.strftime('%d/%m/%Y')} – {nam_hoc.CuoiKII_KetThuc.strftime('%d/%m/%Y')}" if nam_hoc.CuoiKII_BatDau else "Chưa cấu hình"

                if not hop_le:
                    field_errors['ngay_thi'] = f"Ngày thi không hợp lệ! Khoảng thời gian thi {ky_thi} - {hoc_ky} là: {khoang_thoi_gian}"
                    return _render_step1_err(request, field_errors, post_data)

        # Bỏ kiểm tra trùng Buổi (CaThi) vì 1 buổi có thể thi nhiều môn, chỉ cần không trùng giờ (đã kiểm tra bên dưới)
        # Business rule: Kiểm tra tối đa 3 ca/ngày cho 1 khối
        ca_count = LichThi.objects.filter(Khoi_id=khoi_id, NgayThi=ngay_thi).count()
        if ca_count >= 3:
            field_errors['ngay_thi'] = "Khối này đã có 3 ca thi trong ngày. Không thể thêm ca thi mới."
            return _render_step1_err(request, field_errors, post_data)

        # Business rule: Khoảng cách tối thiểu 5 phút giữa các ca trong cùng ngày
        cac_ca_cung_ngay = LichThi.objects.filter(
            Khoi_id=khoi_id,
            NgayThi=ngay_thi
        ).exclude(id=None)

        for ca in cac_ca_cung_ngay:
            # Kiểm tra khoảng cách
            if ca.GioKetThuc <= gio_bat_dau:
                # Ca này kết thúc trước ca mới bắt đầu
                khoang_cach = (datetime.combine(date.today(), gio_bat_dau) -
                               datetime.combine(date.today(), ca.GioKetThuc)).seconds // 60
                if khoang_cach < 5:
                    field_errors['gio_bat_dau'] = "Khoảng cách với ca thi trước phải tối thiểu 5 phút."
                    return _render_step1_err(request, field_errors, post_data)
            elif gio_ket_thuc <= ca.GioBatDau:
                # Ca mới kết thúc trước ca này bắt đầu
                khoang_cach = (datetime.combine(date.today(), ca.GioBatDau) -
                               datetime.combine(date.today(), gio_ket_thuc)).seconds // 60
                if khoang_cach < 5:
                    field_errors['gio_ket_thuc'] = "Khoảng cách với ca thi sau phải tối thiểu 5 phút."
                    return _render_step1_err(request, field_errors, post_data)
            else:
                # Trùng giờ
                field_errors['gio_bat_dau'] = "Giờ thi bị trùng với ca thi khác trong cùng ngày."
                return _render_step1_err(request, field_errors, post_data)
        
        # Lưu vào session để chuyển sang bước 2
        request.session['schedule_step1_data'] = {
            'nam_hoc_id': nam_hoc_id,
            'khoi_id': khoi_id,
            'mon_id': mon_id,
            'hoc_ky': hoc_ky,
            'ky_thi': ky_thi,
            'ca_thi': ca_thi,
            'ngay_thi': ngay_thi_str,
            'gio_bat_dau': gio_bat_dau_str,
            'gio_ket_thuc': gio_ket_thuc_str,
            'ghi_chu': ghi_chu,
        }
        
        return redirect('schedule_create_step2')
    
    context = {
        'step1_data': request.session.get('schedule_step1_data', {}),
        'field_errors': {},
        'nam_hoc_list': NamHoc.objects.all(),
        'khoi_list': Khoi.objects.all(),
        'mon_list': MonHoc.objects.filter(TrangThai='Đang hoạt động'),
    }
    return render(request, 'schedule/create_step1.html', context)


@login_required
@khao_thi_required
def schedule_create_step2(request):
    """
    UC 6.1: Tạo lịch thi - Bước 2 (Chọn đề thi chính thức)
    """
    gv = getattr(request.user, 'giaovien', None)
    if not gv or gv.ChucVu not in ['Hiệu trưởng', 'Phó hiệu trưởng']:
        messages.error(request, "Chỉ Ban Giám Hiệu mới có quyền tạo lịch thi.")
        return redirect('schedule_list')
    
    # Lấy dữ liệu bước 1
    step1_data = request.session.get('schedule_step1_data')
    if not step1_data:
        messages.warning(request, "Vui lòng hoàn thành bước 1 trước.")
        return redirect('schedule_create_step1')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Exception 7a: Hủy thao tác
        if action == 'cancel':
            del request.session['schedule_step1_data']
            messages.info(request, "Đã hủy tạo lịch thi.")
            return redirect('schedule_list')
        
        de_thi_id = request.POST.get('de_thi_id')
        
        # Exception 10a: Chưa chọn đề thi
        if not de_thi_id:
            messages.error(request, "Vui lòng chọn đề thi.")
            return redirect('schedule_create_step2')
        
        # Tạo lịch thi
        try:
            lich_thi = LichThi.objects.create(
                NamHoc_id=step1_data.get('nam_hoc_id') or None,
                Khoi_id=step1_data['khoi_id'],
                MonHoc_id=step1_data['mon_id'],
                HocKy=step1_data['hoc_ky'],
                KyThi=step1_data['ky_thi'],
                CaThi=step1_data['ca_thi'],
                NgayThi=datetime.strptime(step1_data['ngay_thi'], '%Y-%m-%d').date(),
                GioBatDau=datetime.strptime(step1_data['gio_bat_dau'], '%H:%M').time(),
                GioKetThuc=datetime.strptime(step1_data['gio_ket_thuc'], '%H:%M').time(),
                DeThi_id=de_thi_id,
                GhiChu=step1_data.get('ghi_chu', ''),
                NguoiTao=gv,
            )
            
            # Xóa session
            del request.session['schedule_step1_data']
            
            messages.success(request, "Lịch thi đã được thêm mới thành công.")
            return redirect('schedule_list')
            
        except Exception as e:
            messages.error(request, f"Lỗi khi tạo lịch thi: {str(e)}")
            return redirect('schedule_create_step2')
    
    # Exception 8a: Không có đề thi phù hợp
    de_thi_list = DeThi.objects.filter(
        TrangThai='Chính thức',
        NamHoc_id=step1_data['nam_hoc_id'],
        Khoi_id=step1_data['khoi_id'],
        MonHoc_id=step1_data['mon_id'],
        HocKy=step1_data['hoc_ky'],
        KyThi=step1_data['ky_thi'],
        lich_thi__isnull=True  # Chưa được gán cho lịch thi nào
    ).select_related('NguoiTao', 'MaMaTran')
    
    if not de_thi_list.exists():
        messages.warning(request, "Chưa có đề thi chính thức cho môn học và khối đã chọn.")
    
    context = {
        'step1_data': step1_data,
        'de_thi_list': de_thi_list,
        'khoi': Khoi.objects.get(id=step1_data['khoi_id']),
        'mon': MonHoc.objects.get(id=step1_data['mon_id']),
    }
    return render(request, 'schedule/create_step2.html', context)


@login_required
@khao_thi_required
def schedule_edit_step1(request, pk):
    """
    UC 6.2: Sửa lịch thi - Bước 1
    """
    gv = getattr(request.user, 'giaovien', None)
    if not gv or gv.ChucVu not in ['Hiệu trưởng', 'Phó hiệu trưởng']:
        messages.error(request, "Chỉ Ban Giám Hiệu mới có quyền sửa lịch thi.")
        return redirect('schedule_list')
    
    lich_thi = get_object_or_404(LichThi, pk=pk)
    if not lich_thi.can_edit_or_delete:
        messages.error(request, "Không thể chỉnh sửa lịch thi đã diễn ra hoặc trong vòng 7 ngày trước ngày thi.")
        return redirect('schedule_list')
    
    if request.method == 'POST':
        nam_hoc_id = request.POST.get('nam_hoc')
        khoi_id = request.POST.get('khoi')
        mon_id = request.POST.get('mon')
        hoc_ky = request.POST.get('hoc_ky')
        ky_thi = request.POST.get('ky_thi')
        ca_thi = request.POST.get('ca_thi')
        ngay_thi_str = request.POST.get('ngay_thi')
        gio_bat_dau_str = request.POST.get('gio_bat_dau')
        gio_ket_thuc_str = request.POST.get('gio_ket_thuc')
        ghi_chu = request.POST.get('ghi_chu', '')
        
        # Exception 6a: Hủy
        action = request.POST.get('action')
        if action == 'cancel':
            messages.info(request, "Đã hủy chỉnh sửa lịch thi.")
            return redirect('schedule_list')
        
        # Exception 6b: Thiếu trường
        if not all([khoi_id, mon_id, hoc_ky, ky_thi, ca_thi, ngay_thi_str, gio_bat_dau_str, gio_ket_thuc_str]):
            messages.error(request, "Vui lòng điền đầy đủ các trường bắt buộc.")
            return redirect('schedule_edit_step1', pk=pk)
        
        try:
            ngay_thi = datetime.strptime(ngay_thi_str, '%Y-%m-%d').date()
            gio_bat_dau = datetime.strptime(gio_bat_dau_str, '%H:%M').time()
            gio_ket_thuc = datetime.strptime(gio_ket_thuc_str, '%H:%M').time()
        except:
            messages.error(request, "Định dạng ngày hoặc giờ không hợp lệ.")
            return redirect('schedule_edit_step1', pk=pk)
        
        # Exception 6c: Giờ kết thúc < Giờ bắt đầu
        if gio_ket_thuc <= gio_bat_dau:
            messages.error(request, "Giờ kết thúc phải lớn hơn giờ bắt đầu.")
            return redirect('schedule_edit_step1', pk=pk)
            
        # Exception 6c2: Ràng buộc giờ theo ca thi
        if ca_thi == 'Buổi sáng' and gio_bat_dau.hour >= 12:
            messages.error(request, "Buổi sáng phải có giờ bắt đầu trước 12:00 trưa.")
            return redirect('schedule_edit_step1', pk=pk)
        if ca_thi == 'Buổi chiều' and gio_bat_dau.hour < 12:
            messages.error(request, "Buổi chiều phải có giờ bắt đầu từ 12:00 trưa trở đi.")
            return redirect('schedule_edit_step1', pk=pk)
        
        # Exception 6d: Kiểm tra ngày thi nằm trong khoảng thời gian của kỳ thi đã chọn
        if nam_hoc_id:
            nam_hoc = NamHoc.objects.filter(id=nam_hoc_id).first()
            if nam_hoc:
                hop_le = True
                khoang_thoi_gian = ""
                
                if hoc_ky == 'Học kỳ 1' and ky_thi == 'Giữa kỳ':
                    if not (nam_hoc.GiuaKI_BatDau and nam_hoc.GiuaKI_KetThuc) or not (nam_hoc.GiuaKI_BatDau <= ngay_thi <= nam_hoc.GiuaKI_KetThuc):
                        hop_le = False
                        khoang_thoi_gian = f"{nam_hoc.GiuaKI_BatDau.strftime('%d/%m/%Y')} - {nam_hoc.GiuaKI_KetThuc.strftime('%d/%m/%Y')}" if nam_hoc.GiuaKI_BatDau else "Chưa cấu hình"
                elif hoc_ky == 'Học kỳ 1' and ky_thi == 'Cuối kỳ':
                    if not (nam_hoc.CuoiKI_BatDau and nam_hoc.CuoiKI_KetThuc) or not (nam_hoc.CuoiKI_BatDau <= ngay_thi <= nam_hoc.CuoiKI_KetThuc):
                        hop_le = False
                        khoang_thoi_gian = f"{nam_hoc.CuoiKI_BatDau.strftime('%d/%m/%Y')} - {nam_hoc.CuoiKI_KetThuc.strftime('%d/%m/%Y')}" if nam_hoc.CuoiKI_BatDau else "Chưa cấu hình"
                elif hoc_ky == 'Học kỳ 2' and ky_thi == 'Giữa kỳ':
                    if not (nam_hoc.GiuaKII_BatDau and nam_hoc.GiuaKII_KetThuc) or not (nam_hoc.GiuaKII_BatDau <= ngay_thi <= nam_hoc.GiuaKII_KetThuc):
                        hop_le = False
                        khoang_thoi_gian = f"{nam_hoc.GiuaKII_BatDau.strftime('%d/%m/%Y')} - {nam_hoc.GiuaKII_KetThuc.strftime('%d/%m/%Y')}" if nam_hoc.GiuaKII_BatDau else "Chưa cấu hình"
                elif hoc_ky == 'Học kỳ 2' and ky_thi == 'Cuối kỳ':
                    if not (nam_hoc.CuoiKII_BatDau and nam_hoc.CuoiKII_KetThuc) or not (nam_hoc.CuoiKII_BatDau <= ngay_thi <= nam_hoc.CuoiKII_KetThuc):
                        hop_le = False
                        khoang_thoi_gian = f"{nam_hoc.CuoiKII_BatDau.strftime('%d/%m/%Y')} - {nam_hoc.CuoiKII_KetThuc.strftime('%d/%m/%Y')}" if nam_hoc.CuoiKII_BatDau else "Chưa cấu hình"
                
                if not hop_le:
                    messages.error(request, f"Ngày thi không hợp lệ! Khoảng thời gian thi {ky_thi} - {hoc_ky} là: {khoang_thoi_gian}")
                    return redirect('schedule_edit_step1', pk=pk)
        
        # Exception 6a: Không trùng với lịch thi khác
        exists = LichThi.objects.filter(
            Khoi_id=khoi_id,
            CaThi=ca_thi,
            NgayThi=ngay_thi
        ).exclude(pk=pk).exists()
        if exists:
            messages.error(request, f"Đã tồn tại lịch thi khác cho Khối này, {ca_thi} vào ngày {ngay_thi}.")
            return redirect('schedule_edit_step1', pk=pk)
        
        # Business rule: Kiểm tra 3 ca/ngày
        ca_count = LichThi.objects.filter(
            Khoi_id=khoi_id,
            NgayThi=ngay_thi
        ).exclude(pk=pk).count()
        if ca_count >= 3:
            messages.error(request, "Khối này đã có 3 ca thi trong ngày. Không thể cập nhật.")
            return redirect('schedule_edit_step1', pk=pk)
        
        # Business rule: Khoảng cách 5 phút
        cac_ca_cung_ngay = LichThi.objects.filter(
            Khoi_id=khoi_id,
            NgayThi=ngay_thi
        ).exclude(pk=pk)
        
        for ca in cac_ca_cung_ngay:
            if ca.GioKetThuc <= gio_bat_dau:
                khoang_cach = (datetime.combine(date.today(), gio_bat_dau) - 
                               datetime.combine(date.today(), ca.GioKetThuc)).seconds // 60
                if khoang_cach < 5:
                    messages.error(request, f"Khoảng cách với ca thi trước phải tối thiểu 5 phút.")
                    return redirect('schedule_edit_step1', pk=pk)
            elif gio_ket_thuc <= ca.GioBatDau:
                khoang_cach = (datetime.combine(date.today(), ca.GioBatDau) - 
                               datetime.combine(date.today(), gio_ket_thuc)).seconds // 60
                if khoang_cach < 5:
                    messages.error(request, f"Khoảng cách với ca thi sau phải tối thiểu 5 phút.")
                    return redirect('schedule_edit_step1', pk=pk)
            else:
                messages.error(request, "Giờ thi bị trùng với ca thi khác trong cùng ngày.")
                return redirect('schedule_edit_step1', pk=pk)
        
        # Lưu vào session
        request.session['schedule_edit_data'] = {
            'lich_thi_id': pk,
            'nam_hoc_id': nam_hoc_id,
            'khoi_id': khoi_id,
            'mon_id': mon_id,
            'hoc_ky': hoc_ky,
            'ky_thi': ky_thi,
            'ca_thi': ca_thi,
            'ngay_thi': ngay_thi_str,
            'gio_bat_dau': gio_bat_dau_str,
            'gio_ket_thuc': gio_ket_thuc_str,
            'ghi_chu': ghi_chu,
            'khoi_changed': int(khoi_id) != lich_thi.Khoi_id,
            'mon_changed': int(mon_id) != lich_thi.MonHoc_id,
            'ky_thi_changed': hoc_ky != lich_thi.HocKy or ky_thi != lich_thi.KyThi,
        }
        
        return redirect('schedule_edit_step2')
    
    context = {
        'lich_thi': lich_thi,
        'nam_hoc_list': NamHoc.objects.all(),
        'khoi_list': Khoi.objects.all(),
        'mon_list': MonHoc.objects.filter(TrangThai='Đang hoạt động'),
    }
    return render(request, 'schedule/edit_step1.html', context)


@login_required
@khao_thi_required
def schedule_edit_step2(request):
    """
    UC 6.2: Sửa lịch thi - Bước 2 (Chọn lại đề thi nếu cần)
    """
    gv = getattr(request.user, 'giaovien', None)
    if not gv or gv.ChucVu not in ['Hiệu trưởng', 'Phó hiệu trưởng']:
        messages.error(request, "Chỉ Ban Giám Hiệu mới có quyền sửa lịch thi.")
        return redirect('schedule_list')
    
    edit_data = request.session.get('schedule_edit_data')
    if not edit_data:
        messages.warning(request, "Vui lòng hoàn thành bước 1 trước.")
        return redirect('schedule_list')
    
    lich_thi = get_object_or_404(LichThi, pk=edit_data['lich_thi_id'])
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Exception 9a: Hủy
        if action == 'cancel':
            del request.session['schedule_edit_data']
            messages.info(request, "Đã hủy chỉnh sửa lịch thi.")
            return redirect('schedule_list')
        
        de_thi_id = request.POST.get('de_thi_id')
        
        # Exception 9b: Chưa chọn đề thi
        if not de_thi_id:
            messages.error(request, "Vui lòng chọn đề thi.")
            return redirect('schedule_edit_step2')
        
        # Cập nhật lịch thi
        try:
            lich_thi.NamHoc_id = edit_data.get('nam_hoc_id') or None
            lich_thi.Khoi_id = edit_data['khoi_id']
            lich_thi.MonHoc_id = edit_data['mon_id']
            lich_thi.HocKy = edit_data['hoc_ky']
            lich_thi.KyThi = edit_data['ky_thi']
            lich_thi.CaThi = edit_data['ca_thi']
            lich_thi.NgayThi = datetime.strptime(edit_data['ngay_thi'], '%Y-%m-%d').date()
            lich_thi.GioBatDau = datetime.strptime(edit_data['gio_bat_dau'], '%H:%M').time()
            lich_thi.GioKetThuc = datetime.strptime(edit_data['gio_ket_thuc'], '%H:%M').time()
            lich_thi.DeThi_id = de_thi_id
            lich_thi.GhiChu = edit_data.get('ghi_chu', '')
            lich_thi.save()
            
            del request.session['schedule_edit_data']
            
            messages.success(request, "Cập nhật lịch thi thành công.")
            return redirect('schedule_list')
            
        except Exception as e:
            messages.error(request, f"Lỗi khi cập nhật lịch thi: {str(e)}")
            return redirect('schedule_edit_step2')
    
    # Lấy danh sách đề thi phù hợp
    # Exception 7a: Không có đề thi phù hợp sau khi thay đổi khối/môn
    de_thi_list = DeThi.objects.filter(
        TrangThai='Chính thức',
        NamHoc_id=edit_data['nam_hoc_id'],
        Khoi_id=edit_data['khoi_id'],
        MonHoc_id=edit_data['mon_id'],
        HocKy=edit_data['hoc_ky'],
        KyThi=edit_data['ky_thi'],
    ).filter(
        Q(lich_thi__isnull=True) |  # Chưa gán
        Q(id=lich_thi.DeThi_id)  # Hoặc đang gán cho lịch thi hiện tại
    ).select_related('NguoiTao', 'MaMaTran')
    
    if not de_thi_list.exists():
        messages.warning(request, "Chưa có đề thi chính thức cho môn học và khối đã chọn.")
    
    context = {
        'edit_data': edit_data,
        'de_thi_list': de_thi_list,
        'lich_thi': lich_thi,
        'khoi': Khoi.objects.get(id=edit_data['khoi_id']),
        'mon': MonHoc.objects.get(id=edit_data['mon_id']),
    }
    return render(request, 'schedule/edit_step2.html', context)


@login_required
@khao_thi_required
def schedule_delete(request, pk):
    """
    UC 6.3: Xóa lịch thi
    """
    gv = getattr(request.user, 'giaovien', None)
    if not gv or gv.ChucVu not in ['Hiệu trưởng', 'Phó hiệu trưởng']:
        messages.error(request, "Chỉ Ban Giám Hiệu mới có quyền xóa lịch thi.")
        return redirect('schedule_list')
    
    lich_thi = get_object_or_404(LichThi, pk=pk)
    
    if request.method == 'POST':
        if not lich_thi.can_edit_or_delete:
            messages.error(request, "Không thể xóa lịch thi đã diễn ra hoặc trong vòng 7 ngày trước ngày thi.")
            return redirect('schedule_list')
        
        
        try:
            # Hủy liên kết với đề thi (để đề thi có thể gán lại)
            if lich_thi.DeThi:
                lich_thi.DeThi = None
                lich_thi.save()
            
            # Xóa lịch thi
            lich_thi.delete()
            
            messages.success(request, "Xóa lịch thi thành công.")
        except Exception as e:
            # Exception 8a: Đã sử dụng cho phiên làm việc
            messages.error(request, f"Không thể xóa do đã sử dụng cho các phiên làm việc.")
        
        return redirect('schedule_list')
    
    # GET request: hiển thị xác nhận
    return redirect('schedule_list')


@login_required
@khao_thi_required
def schedule_api_mon_theo_khoi(request):
    """API trả về danh sách môn học theo khối (AJAX)"""
    khoi_id = request.GET.get('khoi_id')
    if not khoi_id:
        return JsonResponse({'mon_list': []})
    
    mon_list = MonHoc.objects.filter(
        KhoiApDung__id=khoi_id,
        TrangThai__in=['Đang hoạt động', 'Đang áp dụng']
    ).values('id', 'TenMon').order_by('TenMon')
    
    return JsonResponse({'mon_list': list(mon_list)})
