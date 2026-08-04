from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.decorators import khao_thi_required
from django.db.models import Q
from datetime import datetime, date

from core.models import NamHoc, Khoi, MonHoc, GiaoVien, LopHoc, PhanCongGiangDay
from .models import LichThi, PhanCongGiamThi, HOC_KY_CHOICES, KY_THI_CHOICES
from .services import auto_assign_invigilators

def check_is_bgh(user):
    if user.is_superuser:
        return True
    gv = getattr(user, 'giaovien', None)
    if gv and gv.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
        return True
    return False

@login_required
@khao_thi_required
def assignment_list(request):
    """
    UC 8.4: Tìm kiếm phân công
    """
    gv = getattr(request.user, 'giaovien', None)
    is_bgh = check_is_bgh(request.user)
    
    query = request.GET.get('q', '')
    nam_hoc_id = request.GET.get('nam_hoc')
    hoc_ky = request.GET.get('hoc_ky')
    ky_thi = request.GET.get('ky_thi')
    khoi_id = request.GET.get('khoi')
    
    phan_cong_list = PhanCongGiamThi.objects.select_related('LichThi', 'LopHoc', 'GiamThi1', 'GiamThi2', 'LichThi__Khoi', 'LichThi__MonHoc').all()
    
    if query:
        phan_cong_list = phan_cong_list.filter(
            Q(LopHoc__TenLop__icontains=query) |
            Q(GiamThi1__HoTen__icontains=query) |
            Q(GiamThi2__HoTen__icontains=query) |
            Q(GiamThiTHCS__icontains=query) |
            Q(LichThi__MonHoc__TenMon__icontains=query)
        )
        
    if nam_hoc_id:
        phan_cong_list = phan_cong_list.filter(LichThi__NamHoc_id=nam_hoc_id)
    if hoc_ky:
        phan_cong_list = phan_cong_list.filter(LichThi__HocKy=hoc_ky)
    if ky_thi:
        phan_cong_list = phan_cong_list.filter(LichThi__KyThi=ky_thi)
    if khoi_id:
        phan_cong_list = phan_cong_list.filter(LichThi__Khoi_id=khoi_id)
        
    phan_cong_list = phan_cong_list.order_by('-LichThi__NamHoc__TenNamHoc', 'LichThi__HocKy', 'LichThi__KyThi', 'LichThi__Khoi__TenKhoi', 'LopHoc__TenLop')
    
    import collections
    grouped_data = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(list)))
    for pc in phan_cong_list:
        nam_hoc = f"Năm học {pc.LichThi.NamHoc.TenNamHoc}"
        hk_kt = f"{pc.LichThi.HocKy} - {pc.LichThi.KyThi}"
        khoi = pc.LichThi.Khoi.TenKhoi
        grouped_data[nam_hoc][hk_kt][khoi].append(pc)
        
    # Chuyển đổi thành dict thông thường cho template
    grouped_data_dict = {
        k: {
            k2: dict(v2) for k2, v2 in v.items()
        } for k, v in grouped_data.items()
    }
    
    context = {
        'grouped_data': grouped_data_dict,
        'nam_hoc_list': NamHoc.objects.all(),
        'khoi_list': Khoi.objects.all(),
        'hoc_ky_choices': HOC_KY_CHOICES,
        'ky_thi_choices': KY_THI_CHOICES,
        'giao_vien_list': GiaoVien.objects.filter(TrangThai='Đang hoạt động'),
        'is_bgh': is_bgh,
    }
    return render(request, 'schedule/assignment/list.html', context)


@login_required
@khao_thi_required
def assignment_auto_config(request):
    """
    UC 9.1: Màn hình lựa chọn Lịch thi để phân công
    """
    if not check_is_bgh(request.user):
        messages.error(request, 'Bạn không có quyền thực hiện chức năng này.')
        return redirect('assignment_list')
        
    # Exception 8a: Hệ thống không có dữ liệu giáo viên hoặc lớp học
    active_teachers_exist = GiaoVien.objects.filter(TrangThai='Đang hoạt động').exclude(
        ChucVu__in=['Hiệu trưởng', 'Phó hiệu trưởng', 'Nhân viên văn thư', 'Admin/Giáo vụ']
    ).exists()
    classes_exist = LopHoc.objects.exists()
    if not active_teachers_exist or not classes_exist:
        messages.error(request, 'Không có giáo viên hoặc lớp học để phân công')
        return redirect('assignment_list')
        
    if request.method == 'POST':
        nam_hoc_id = request.POST.get('nam_hoc')
        hoc_ky = request.POST.get('hoc_ky')
        ky_thi = request.POST.get('ky_thi')
        
        if not nam_hoc_id or not hoc_ky or not ky_thi:
            messages.error(request, 'Vui lòng chọn đầy đủ Năm học, Học kỳ, Kỳ thi.')
            return redirect('assignment_auto_config')
            
        # Exception 6b: Phát hiện lịch thi đã chọn đã tồn tại phân công giám thị từ trước
        if PhanCongGiamThi.objects.filter(
            LichThi__NamHoc_id=nam_hoc_id, 
            LichThi__HocKy=hoc_ky, 
            LichThi__KyThi=ky_thi
        ).exists():
            messages.error(request, 'Lịch thi này đã có phân công')
            return redirect('assignment_auto_config')
            
        lich_thi_list = LichThi.objects.filter(
            NamHoc_id=nam_hoc_id, HocKy=hoc_ky, KyThi=ky_thi
        ).filter(phan_cong_set__isnull=True)
        
        # Exception 6a: Hệ thống không tìm thấy lịch thi hoặc lịch thi chưa hoàn tất
        if not lich_thi_list.exists():
            messages.error(request, 'Không có tìm thấy lịch thi')
            return redirect('assignment_auto_config')
            
        request.session['auto_assign_config'] = {
            'nam_hoc_id': nam_hoc_id,
            'hoc_ky': hoc_ky,
            'ky_thi': ky_thi
        }
        return redirect('assignment_auto_preview')
        
    context = {
        'nam_hoc_list': NamHoc.objects.all(),
        'hoc_ky_choices': HOC_KY_CHOICES,
        'ky_thi_choices': KY_THI_CHOICES,
    }
    return render(request, 'schedule/assignment/auto_step1.html', context)


@login_required
@khao_thi_required
def assignment_auto_preview(request):
    config = request.session.get('auto_assign_config')
    if not config:
        messages.warning(request, 'Vui lòng chọn đợt thi trước.')
        return redirect('assignment_auto_config')
        
    nam_hoc_id = config['nam_hoc_id']
    hoc_ky = config['hoc_ky']
    ky_thi = config['ky_thi']
    
    lich_thi_list = list(LichThi.objects.filter(
        NamHoc_id=nam_hoc_id, HocKy=hoc_ky, KyThi=ky_thi
    ).filter(phan_cong_set__isnull=True).order_by('NgayThi', 'GioBatDau'))
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'cancel':
            del request.session['auto_assign_config']
            if 'auto_assign_results' in request.session:
                del request.session['auto_assign_results']
            return redirect('assignment_list')
            
        elif action == 'save':
            results = request.session.get('auto_assign_results', [])
            if not results:
                messages.error(request, 'Không có dữ liệu phân công để lưu.')
                return redirect('assignment_auto_preview')
                
            for res in results:
                thcs = request.POST.get(f'thcs_{res["lop_hoc_id"]}_{res["lich_thi_id"]}', '')
                
                if PhanCongGiamThi.objects.filter(LichThi_id=res['lich_thi_id'], LopHoc_id=res['lop_hoc_id']).exists():
                    continue
                    
                PhanCongGiamThi.objects.create(
                    LichThi_id=res['lich_thi_id'],
                    LopHoc_id=res['lop_hoc_id'],
                    GiamThi1_id=res['giam_thi_1_id'],
                    GiamThi2_id=res['giam_thi_2_id'],
                    GiamThiTHCS=thcs
                )
            
            messages.success(request, 'Lưu phân công giám thị thành công.')
            del request.session['auto_assign_config']
            del request.session['auto_assign_results']
            return redirect('assignment_list')
            
        elif action == 'rerun':
            thcs_data = {}
            results = request.session.get('auto_assign_results', [])
            for res in results:
                val = request.POST.get(f'thcs_{res["lop_hoc_id"]}_{res["lich_thi_id"]}')
                if val:
                    thcs_data[f'{res["lop_hoc_id"]}_{res["lich_thi_id"]}'] = val
            
            new_results, errors = auto_assign_invigilators(lich_thi_list)
            
            for res in new_results:
                key = f'{res["lop_hoc_id"]}_{res["lich_thi_id"]}'
                if key in thcs_data:
                    res['giam_thi_thcs'] = thcs_data[key]
                    
            request.session['auto_assign_results'] = new_results
            if errors:
                for e in errors:
                    messages.warning(request, e)
            
            return render(request, 'schedule/assignment/auto_step2.html', {
                'results': new_results,
            })
            
    if 'auto_assign_results' not in request.session:
        results, errors = auto_assign_invigilators(lich_thi_list)
        request.session['auto_assign_results'] = results
        if errors:
            for e in errors:
                messages.warning(request, e)
    else:
        results = request.session['auto_assign_results']
        
    return render(request, 'schedule/assignment/auto_step2.html', {
        'results': results,
    })


@login_required
@khao_thi_required
def assignment_edit(request, pk):
    """
    UC 9.2: Sửa phân công giám thị
    """
    if not check_is_bgh(request.user):
        messages.error(request, 'Bạn không có quyền thực hiện chức năng này.')
        return redirect('assignment_list')
        
    phan_cong = get_object_or_404(PhanCongGiamThi, pk=pk)
    
    if not phan_cong.can_edit:
        messages.error(request, 'Không thể thực hiện sửa do đã sử dụng cho các phiên làm việc.')
        return redirect('assignment_list')
        
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'cancel':
            return redirect('assignment_list')
            
        giam_thi_1_id = request.POST.get('giam_thi_1') or None
        giam_thi_2_id = request.POST.get('giam_thi_2') or None
        giam_thi_thcs = request.POST.get('giam_thi_thcs', '').strip()
        
        referer = request.META.get('HTTP_REFERER', 'assignment_list')
        
        if (giam_thi_1_id and not GiaoVien.objects.filter(id=giam_thi_1_id).exists()) or \
           (giam_thi_2_id and not GiaoVien.objects.filter(id=giam_thi_2_id).exists()):
            messages.error(request, 'Không có giáo viên hoặc lớp học để phân công')
            return redirect(referer)

        # Validate logic (Rule 2: GVCN không coi lớp mình)
        if str(phan_cong.LopHoc.GVCN_id) in [giam_thi_1_id, giam_thi_2_id]:
            messages.error(request, 'Giáo viên không thể coi thi tại lớp mình đang chủ nhiệm.')
            return redirect(referer)
            
        def check_teacher_overlap(gv_id):
            overlap = PhanCongGiamThi.objects.filter(
                Q(GiamThi1_id=gv_id) | Q(GiamThi2_id=gv_id),
                LichThi__NgayThi=phan_cong.LichThi.NgayThi
            ).exclude(pk=pk)
            for ov in overlap:
                if max(phan_cong.LichThi.GioBatDau, ov.LichThi.GioBatDau) < min(phan_cong.LichThi.GioKetThuc, ov.LichThi.GioKetThuc):
                    return True
            return False
            
        # Check GV1 overlap
        if giam_thi_1_id and check_teacher_overlap(giam_thi_1_id):
            messages.error(request, 'Giáo viên trùng lịch thi')
            return redirect(referer)
                    
        # Check GV2 overlap
        if giam_thi_2_id and check_teacher_overlap(giam_thi_2_id):
            messages.error(request, 'Giáo viên trùng lịch thi')
            return redirect(referer)
            
        # Validate rules theo khối
        def validate_khoi_rule(gv_id, is_gt1=True):
            if not gv_id: return None
            teaching_assignments = PhanCongGiangDay.objects.filter(GiaoVien_id=gv_id)
            teaching_khoi_ids = set(teaching_assignments.values_list('LopHoc__Khoi_id', flat=True))
            teaching_khoi_names = set(Khoi.objects.filter(id__in=teaching_khoi_ids).values_list('TenKhoi', flat=True))
            khoi_name = phan_cong.LichThi.Khoi.TenKhoi
            
            if '1' in khoi_name:
                if not any('1' in kn or '2' in kn for kn in teaching_khoi_names):
                    return "Khối 1: Giám thị phải là GV dạy Khối 1 hoặc Khối 2."
            elif '2' in khoi_name or '3' in khoi_name:
                if khoi_name in teaching_khoi_names:
                    return f"Khối 2, 3: Giáo viên không được dạy {khoi_name}."
            elif '4' in khoi_name or '5' in khoi_name:
                if khoi_name in teaching_khoi_names:
                    return f"Khối 4, 5: Giáo viên không được dạy {khoi_name}."
            return None
            
        err1 = validate_khoi_rule(giam_thi_1_id, True)
        if err1:
            messages.error(request, err1)
            return redirect(referer)
            
        err2 = validate_khoi_rule(giam_thi_2_id, False)
        if err2:
            messages.error(request, err2)
            return redirect(referer)
        
        phan_cong.GiamThi1_id = giam_thi_1_id
        phan_cong.GiamThi2_id = giam_thi_2_id
        phan_cong.GiamThiTHCS = giam_thi_thcs
        phan_cong.save()
        messages.success(request, 'Cập nhật phân công thành công.')
        return redirect(referer)
        
    giao_vien_list = GiaoVien.objects.filter(TrangThai='Đang hoạt động')
    context = {
        'phan_cong': phan_cong,
        'giao_vien_list': giao_vien_list,
        'is_k5_toan_tv': '5' in phan_cong.LichThi.Khoi.TenKhoi and phan_cong.LichThi.MonHoc.TenMon in ['Toán', 'Tiếng Việt']
    }
    return render(request, 'schedule/assignment/edit.html', context)


@login_required
@khao_thi_required
def assignment_delete(request, pk):
    """
    UC 14.3: Xóa phân công giám thị
    """
    if not check_is_bgh(request.user):
        messages.error(request, 'Bạn không có quyền thực hiện chức năng này.')
        return redirect('assignment_list')
        
    phan_cong = get_object_or_404(PhanCongGiamThi, pk=pk)
    
    # 5a. Hồ sơ đã sử dụng cho các phiên làm việc (đã bắt đầu hoặc kết thúc)
    from datetime import date
    import django.utils.timezone as tz
    today = date.today()
    
    is_ongoing_or_past = False
    if phan_cong.LichThi.NgayThi < today:
        is_ongoing_or_past = True
    elif phan_cong.LichThi.NgayThi == today:
        now = tz.localtime(tz.now()).time()
        if phan_cong.LichThi.GioBatDau <= now:
            is_ongoing_or_past = True
            
    if is_ongoing_or_past:
        messages.error(request, "Không thể xóa do đã sử dụng cho các phiên làm việc.")
        return redirect('assignment_list')
        
    # Business rule 2: Không cho phép xóa khi trước ngày bắt đầu thi 5 ngày
    days_until_exam = (phan_cong.LichThi.NgayThi - today).days
    if days_until_exam < 5:
        messages.error(request, "Không thể xóa phân công giám thị trong vòng 5 ngày trước ngày thi.")
        return redirect('assignment_list')
        
    if request.method == 'POST':
        phan_cong.delete()
        messages.success(request, "Xóa phân công thành công.")
        return redirect('assignment_list')
        
    return redirect('assignment_list')



