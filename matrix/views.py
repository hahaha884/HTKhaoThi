import unicodedata
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone

from core.decorators import khao_thi_required
from core.models import NamHoc, Khoi, MonHoc, GiaoVien
from question_bank.models import MachKienThuc, NoiDungKienThuc
from .models import MaTran, CT_MaTran, LichSuPheDuyetMaTran, DeadlineGiaoVien
from .services import validate_matrix_data, generate_matrix_docx


@login_required
@khao_thi_required
def matrix_list(request):
    """
    UC 9.4: Tìm kiếm và lọc danh sách ma trận đề thi
    Hỗ trợ tìm theo từ khóa và các bộ lọc kết hợp (AND logic).
    """
    matrans = MaTran.objects.all().select_related('NamHoc', 'Khoi', 'MonHoc', 'NguoiTao').order_by('-NgayCapNhat')

    # Phân quyền hiển thị theo chức vụ
    if not request.user.is_superuser:
        try:
            gv = request.user.giaovien
            if gv.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
                # BGH thấy: Chờ duyệt, Đã duyệt, Từ chối của tất cả, và Nháp của chính mình
                matrans = matrans.filter(Q(NguoiTao=gv) | Q(TrangThai__in=['Chờ duyệt', 'Đã duyệt', 'Từ chối']))
            elif gv.ChucVu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
                # TCM thấy: Đã duyệt, Nháp/Chờ duyệt/Từ chối của chính mình
                matrans = matrans.filter(Q(NguoiTao=gv) | Q(TrangThai='Đã duyệt'))
            else:
                # GV chỉ thấy các ma trận đã được duyệt
                matrans = matrans.filter(TrangThai='Đã duyệt')
        except Exception:
            matrans = matrans.filter(TrangThai='Đã duyệt')

    # Bộ lọc & Tìm kiếm (UC 9.4)
    search_keyword = (request.GET.get('search') or '').strip()
    namhoc = request.GET.get('namhoc')
    hocky = request.GET.get('hocky')
    kythi = request.GET.get('kythi')
    monhoc = request.GET.get('monhoc')
    khoi = request.GET.get('khoi')
    trangthai = request.GET.get('trangthai')
    nguoitao = request.GET.get('nguoitao')

    is_filtered = bool(search_keyword or namhoc or hocky or kythi or monhoc or khoi or trangthai or nguoitao)

    if search_keyword:
        matrans = matrans.filter(TenMaTran__icontains=search_keyword)
    if namhoc:
        matrans = matrans.filter(NamHoc_id=namhoc)
    if hocky:
        matrans = matrans.filter(HocKy=hocky)
    if kythi:
        matrans = matrans.filter(KyThi=kythi)
    if monhoc:
        matrans = matrans.filter(MonHoc_id=monhoc)
    if khoi:
        matrans = matrans.filter(Khoi_id=khoi)
    if trangthai:
        matrans = matrans.filter(TrangThai=trangthai)
    if nguoitao:
        matrans = matrans.filter(NguoiTao_id=nguoitao)

    paginator = Paginator(matrans, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    is_bgh = False
    if hasattr(request.user, 'giaovien') and request.user.giaovien.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
        is_bgh = True

    context = {
        'matrans': page_obj,
        'page_obj': page_obj,
        'namhocs': NamHoc.objects.all(),
        'khois': Khoi.objects.all(),
        'monhocs': MonHoc.objects.all(),
        'giaoviens': GiaoVien.objects.all(),
        'is_bgh': is_bgh,
        'is_filtered': is_filtered,
        'today': date.today(),
    }
    return render(request, 'matrix/list.html', context)


@login_required
@khao_thi_required
def matrix_create(request):
    """
    UC 9.1: Thêm ma trận đề thi và nộp phê duyệt.
    """
    # Kiểm tra phân quyền: Chỉ Tổ chuyên môn (Tổ trưởng, Tổ phó) hoặc Superuser. BGH không được tạo ma trận.
    gv = getattr(request.user, 'giaovien', None)
    if not request.user.is_superuser:
        if not gv or gv.ChucVu not in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
            messages.error(request, 'Chỉ Tổ chuyên môn mới có quyền tạo ma trận đề thi. Ban Giám hiệu không có quyền thực hiện thao tác này.')
            return redirect('matrix_list')

    context = {
        'namhocs': NamHoc.objects.all(),
        'khois': Khoi.objects.all(),
        'monhocs': MonHoc.objects.all(),
        'machs': MachKienThuc.objects.all(),
        'noidungs': NoiDungKienThuc.objects.all(),
    }

    if request.method == 'POST':
        action = 'submit'

        ten_matran = (request.POST.get('TenMaTran') or '').strip()
        nam_hoc_id = request.POST.get('NamHoc')
        hoc_ky = request.POST.get('HocKy')
        ky_thi = request.POST.get('KyThi')
        khoi_id = request.POST.get('Khoi')
        mon_hoc_id = request.POST.get('MonHoc')
        mo_ta = request.POST.get('MoTa', '')

        mach_ids = request.POST.getlist('MachKienThuc[]')
        noidung_ids = request.POST.getlist('NoiDung[]')
        mucdos = request.POST.getlist('MucDo[]')
        loais = request.POST.getlist('LoaiCauHoi[]')
        soluongs = request.POST.getlist('SoLuongCau[]')
        causos = request.POST.getlist('CauSo[]')
        diems = request.POST.getlist('Diem[]')
        tyles = request.POST.getlist('TyLe[]')

        header_data = {
            'TenMaTran': ten_matran,
            'NamHoc': nam_hoc_id,
            'HocKy': hoc_ky,
            'KyThi': ky_thi,
            'Khoi': khoi_id,
            'MonHoc': mon_hoc_id,
            'MoTa': mo_ta,
        }

        details_data = []
        for i in range(len(mach_ids)):
            details_data.append({
                'MachKienThuc': mach_ids[i],
                'NoiDung': noidung_ids[i],
                'MucDo': mucdos[i] if i < len(mucdos) else '',
                'LoaiCauHoi': loais[i] if i < len(loais) else '',
                'SoLuongCau': soluongs[i] if i < len(soluongs) else '',
                'CauSo': causos[i] if i < len(causos) else '',
                'Diem': diems[i] if i < len(diems) else '',
                'TyLe': tyles[i] if i < len(tyles) else '',
            })

        val_result = validate_matrix_data(header_data, details_data, action=action)

        if not val_result['is_valid']:
            for err in val_result['errors']:
                messages.error(request, err)

            # Đóng gói dữ liệu postback
            matran_mock = MaTran(
                TenMaTran=ten_matran,
                NamHoc_id=nam_hoc_id,
                HocKy=hoc_ky,
                KyThi=ky_thi,
                Khoi_id=khoi_id,
                MonHoc_id=mon_hoc_id,
                MoTa=mo_ta,
            )
            context['matran'] = matran_mock
            context['posted_details'] = [
                {
                    'MachKienThuc_id': int(d['MachKienThuc']) if d['MachKienThuc'] else None,
                    'NoiDung_id': int(d['NoiDung']) if d['NoiDung'] else None,
                    'MucDo': d['MucDo'],
                    'LoaiCauHoi': d['LoaiCauHoi'],
                    'SoLuongCau': d['SoLuongCau'],
                    'CauSo': d['CauSo'],
                    'Diem': d['Diem'],
                    'TyLe': d['TyLe'],
                }
                for d in details_data
            ]
            context['row_errors'] = val_result['row_errors']
            context['level_errors'] = val_result['level_errors']
            context['is_post_back'] = True
            return render(request, 'matrix/form.html', context)

        # Dữ liệu hợp lệ -> Tính toán và Lưu
        calc = val_result['calc_summary']
        tong_so_cau = calc.get('tong_so_cau', 0)
        tong_diem = calc.get('tong_diem', 0.0)

        trang_thai = 'Chờ duyệt'

        try:
            with transaction.atomic():
                creator = gv
                if not creator and request.user.is_superuser:
                    creator = GiaoVien.objects.first()

                matran = MaTran.objects.create(
                    NguoiTao=creator,
                    TenMaTran=ten_matran,
                    NamHoc_id=nam_hoc_id,
                    HocKy=hoc_ky,
                    KyThi=ky_thi,
                    Khoi_id=khoi_id,
                    MonHoc_id=mon_hoc_id,
                    MoTa=mo_ta,
                    TongSoCau=tong_so_cau,
                    TongSoDiem=tong_diem,
                    TrangThai=trang_thai
                )

                for row in details_data:
                    if row['MachKienThuc'] and row['NoiDung']:
                        CT_MaTran.objects.create(
                            MaTran=matran,
                            MachKienThuc_id=row['MachKienThuc'],
                            NoiDung_id=row['NoiDung'],
                            MucDo=row['MucDo'],
                            LoaiCauHoi=row['LoaiCauHoi'],
                            SoLuongCau=int(row['SoLuongCau']) if row['SoLuongCau'] else 0,
                            CauSo=row['CauSo'],
                            Diem=float(row['Diem']) if row['Diem'] else 0.0,
                            TyLe=float(row['TyLe']) if row['TyLe'] else 0.0
                        )

                messages.success(request, 'Thêm và gửi đi ma trận thành công.')
                return redirect('matrix_list')

        except IntegrityError:
            messages.error(request, 'Ma trận đã tồn tại.')
            context['matran'] = MaTran(
                TenMaTran=ten_matran, NamHoc_id=nam_hoc_id, HocKy=hoc_ky,
                KyThi=ky_thi, Khoi_id=khoi_id, MonHoc_id=mon_hoc_id, MoTa=mo_ta
            )
            context['is_post_back'] = True
            return render(request, 'matrix/form.html', context)
        except Exception as e:
            messages.error(request, f'Lỗi hệ thống: {str(e)}')
            return render(request, 'matrix/form.html', context)

    return render(request, 'matrix/form.html', context)


@login_required
@khao_thi_required
def matrix_update(request, pk):
    """
    UC 9.2: Sửa ma trận đề thi
    Chỉ cho phép sửa khi ma trận ở trạng thái 'Nháp'.
    """
    matran = get_object_or_404(MaTran, pk=pk)
    gv = getattr(request.user, 'giaovien', None)

    # Phân quyền: Người tạo hoặc Admin/BGH
    if not request.user.is_superuser:
        if matran.NguoiTao != gv and (not gv or gv.ChucVu not in ['Hiệu trưởng', 'Phó hiệu trưởng']):
            messages.error(request, 'Bạn không có quyền sửa ma trận của người khác.')
            return redirect('matrix_list')

    # Pre-condition: Chỉ được sửa khi đang ở trạng thái Nháp
    if matran.TrangThai != 'Nháp':
        messages.error(request, 'Bạn chỉ có thể sửa ma trận khi đang ở trạng thái Nháp.')
        return redirect('matrix_list')

    context = {
        'matran': matran,
        'namhocs': NamHoc.objects.all(),
        'khois': Khoi.objects.all(),
        'monhocs': MonHoc.objects.all(),
        'machs': MachKienThuc.objects.all(),
        'noidungs': NoiDungKienThuc.objects.all(),
        'has_details': matran.chi_tiet.exists(),
    }

    if request.method == 'POST':
        action = 'submit'

        new_ten = (request.POST.get('TenMaTran') or '').strip()
        new_nam = request.POST.get('NamHoc')
        new_hocky = request.POST.get('HocKy')
        new_kythi = request.POST.get('KyThi')
        new_khoi = request.POST.get('Khoi')
        new_mon = request.POST.get('MonHoc')
        new_mota = request.POST.get('MoTa', '')

        mach_ids = request.POST.getlist('MachKienThuc[]')
        noidung_ids = request.POST.getlist('NoiDung[]')
        mucdos = request.POST.getlist('MucDo[]')
        loais = request.POST.getlist('LoaiCauHoi[]')
        soluongs = request.POST.getlist('SoLuongCau[]')
        causos = request.POST.getlist('CauSo[]')
        diems = request.POST.getlist('Diem[]')
        tyles = request.POST.getlist('TyLe[]')

        header_data = {
            'TenMaTran': new_ten,
            'NamHoc': new_nam,
            'HocKy': new_hocky,
            'KyThi': new_kythi,
            'Khoi': new_khoi,
            'MonHoc': new_mon,
            'MoTa': new_mota,
        }

        details_data = []
        for i in range(len(mach_ids)):
            details_data.append({
                'MachKienThuc': mach_ids[i],
                'NoiDung': noidung_ids[i],
                'MucDo': mucdos[i] if i < len(mucdos) else '',
                'LoaiCauHoi': loais[i] if i < len(loais) else '',
                'SoLuongCau': soluongs[i] if i < len(soluongs) else '',
                'CauSo': causos[i] if i < len(causos) else '',
                'Diem': diems[i] if i < len(diems) else '',
                'TyLe': tyles[i] if i < len(tyles) else '',
            })

        val_result = validate_matrix_data(header_data, details_data, action=action, existing_matran_id=matran.pk)

        if not val_result['is_valid']:
            for err in val_result['errors']:
                messages.error(request, err)

            matran.TenMaTran = new_ten
            matran.NamHoc_id = new_nam
            matran.HocKy = new_hocky
            matran.KyThi = new_kythi
            matran.Khoi_id = new_khoi
            matran.MonHoc_id = new_mon
            matran.MoTa = new_mota

            context['matran'] = matran
            context['posted_details'] = [
                {
                    'MachKienThuc_id': int(d['MachKienThuc']) if d['MachKienThuc'] else None,
                    'NoiDung_id': int(d['NoiDung']) if d['NoiDung'] else None,
                    'MucDo': d['MucDo'],
                    'LoaiCauHoi': d['LoaiCauHoi'],
                    'SoLuongCau': d['SoLuongCau'],
                    'CauSo': d['CauSo'],
                    'Diem': d['Diem'],
                    'TyLe': d['TyLe'],
                }
                for d in details_data
            ]
            context['row_errors'] = val_result['row_errors']
            context['level_errors'] = val_result['level_errors']
            context['is_post_back'] = True
            return render(request, 'matrix/form.html', context)

        # Hợp lệ -> Cập nhật
        calc = val_result['calc_summary']
        matran.TenMaTran = new_ten
        matran.NamHoc_id = new_nam
        matran.HocKy = new_hocky
        matran.KyThi = new_kythi
        matran.Khoi_id = new_khoi
        matran.MonHoc_id = new_mon
        matran.MoTa = new_mota
        matran.TongSoCau = calc.get('tong_so_cau', 0)
        matran.TongSoDiem = calc.get('tong_diem', 0.0)
        matran.TrangThai = 'Chờ duyệt'

        try:
            with transaction.atomic():
                matran.save()
                CT_MaTran.objects.filter(MaTran=matran).delete()

                for row in details_data:
                    if row['MachKienThuc'] and row['NoiDung']:
                        CT_MaTran.objects.create(
                            MaTran=matran,
                            MachKienThuc_id=row['MachKienThuc'],
                            NoiDung_id=row['NoiDung'],
                            MucDo=row['MucDo'],
                            LoaiCauHoi=row['LoaiCauHoi'],
                            SoLuongCau=int(row['SoLuongCau']) if row['SoLuongCau'] else 0,
                            CauSo=row['CauSo'],
                            Diem=float(row['Diem']) if row['Diem'] else 0.0,
                            TyLe=float(row['TyLe']) if row['TyLe'] else 0.0
                        )

                messages.success(request, 'Cập nhật và gửi đi ma trận thành công.')
                return redirect('matrix_list')

        except IntegrityError:
            messages.error(request, 'Ma trận đã tồn tại.')
            return render(request, 'matrix/form.html', context)
        except Exception as e:
            messages.error(request, f'Lỗi hệ thống: {str(e)}')
            return render(request, 'matrix/form.html', context)

    return render(request, 'matrix/form.html', context)


@login_required
@khao_thi_required
def matrix_delete(request, pk):
    """
    UC 9.3: Xóa ma trận đề thi
    Chỉ cho phép xóa ma trận ở trạng thái 'Nháp'.
    Không được xóa ma trận đã được phê duyệt.
    """
    matran = get_object_or_404(MaTran, pk=pk)

    if request.method == 'POST':
        gv = getattr(request.user, 'giaovien', None)
        if not request.user.is_superuser:
            if matran.NguoiTao != gv and (not gv or gv.ChucVu not in ['Hiệu trưởng', 'Phó hiệu trưởng']):
                messages.error(request, 'Bạn không có quyền xóa ma trận của người khác.')
                return redirect('matrix_list')

        # 8b: Ma trận đã được phê duyệt
        if matran.TrangThai == 'Đã duyệt':
            messages.error(request, 'Không thể xóa ma trận đã được phê duyệt.')
            return redirect('matrix_list')

        if matran.TrangThai != 'Nháp':
            messages.error(request, 'Chỉ có thể xóa ma trận ở trạng thái Nháp.')
            return redirect('matrix_list')

        matran.delete()
        messages.success(request, 'Xóa ma trận thành công.')

    return redirect('matrix_list')


@login_required
@khao_thi_required
def matrix_detail(request, pk):
    """
    Hiển thị thông tin chi tiết ma trận, thống kê mức độ, lịch sử phê duyệt.
    """
    matran = get_object_or_404(MaTran, pk=pk)
    chi_tiet = matran.chi_tiet.all().select_related('MachKienThuc', 'NoiDung')

    is_bgh = False
    is_owner = False
    gv = getattr(request.user, 'giaovien', None)
    if gv:
        if gv.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
            is_bgh = True
        if matran.NguoiTao == gv:
            is_owner = True
    if request.user.is_superuser:
        is_bgh = True
        is_owner = True

    # Kiểm tra quyền xem chi tiết (Object-level permission)
    if not request.user.is_superuser and not is_bgh and not is_owner:
        if matran.TrangThai != 'Đã duyệt':
            messages.error(request, 'Bạn không có quyền xem ma trận này khi chưa được phê duyệt.')
            return redirect('matrix_list')

    # Thống kê mức độ nhận thức
    muc_stats = {
        'Mức 1': {'cau': 0, 'diem': 0.0, 'tyle': 0.0, 'thucte': 0.0},
        'Mức 2': {'cau': 0, 'diem': 0.0, 'tyle': 0.0, 'thucte': 0.0},
        'Mức 3': {'cau': 0, 'diem': 0.0, 'tyle': 0.0, 'thucte': 0.0},
    }
    for ct in chi_tiet:
        if ct.MucDo in muc_stats:
            muc_stats[ct.MucDo]['cau'] += ct.SoLuongCau
            muc_stats[ct.MucDo]['diem'] += ct.Diem
            muc_stats[ct.MucDo]['tyle'] += ct.TyLe

    if matran.TongSoDiem > 0:
        for m in muc_stats:
            pct = (muc_stats[m]['diem'] / matran.TongSoDiem) * 100
            muc_stats[m]['thucte'] = round(pct, 1)
            muc_stats[m]['lamtron'] = int(round(pct / 10) * 10)

    lich_su = matran.lich_su.all().order_by('-ThoiGian')

    is_tcm = False
    if gv and gv.ChucVu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
        is_tcm = True
    if request.user.is_superuser:
        is_tcm = True

    from core.models import GiaoVien as GV_Model
    gv_list_for_deadline = GV_Model.objects.exclude(
        TrangThai='Dừng hoạt động'
    ).exclude(
        ChucVu__in=['Hiệu trưởng', 'Phó hiệu trưởng', 'Nhân viên văn thư']
    ).order_by('ChucVu', 'HoTen')

    deadlines_gv = matran.deadline_gv.select_related('GiaoVien', 'NguoiSet').all()

    context = {
        'matran': matran,
        'chi_tiet': chi_tiet,
        'is_bgh': is_bgh,
        'is_owner': is_owner,
        'is_tcm': is_tcm,
        'lich_su': lich_su,
        'muc_stats': muc_stats,
        'gv_list_for_deadline': gv_list_for_deadline,
        'deadlines_gv': deadlines_gv,
        'today': date.today(),
    }
    return render(request, 'matrix/detail.html', context)


@login_required
@khao_thi_required
def matrix_approve(request, pk):
    """
    Phê duyệt hoặc từ chối ma trận đề thi (dành cho Ban Giám Hiệu).
    Khi duyệt, BGH có thể nhập DeadlineNopDe (hạn nộp đề thi cho TCM).
    """
    matran = get_object_or_404(MaTran, pk=pk)

    if request.method == 'POST':
        gv = getattr(request.user, 'giaovien', None)
        if not request.user.is_superuser:
            if not gv or gv.ChucVu not in ['Hiệu trưởng', 'Phó hiệu trưởng']:
                messages.error(request, 'Chỉ Ban Giám Hiệu mới có quyền phê duyệt.')
                return redirect('matrix_detail', pk=pk)

        action = request.POST.get('action')
        ghi_chu = (request.POST.get('GhiChu') or '').strip()
        deadline_nop_str = request.POST.get('DeadlineNopDe', '').strip()
        deadline_sua_str = request.POST.get('DeadlineSuaDe', '').strip()

        trang_thai_moi = 'Đã duyệt' if action == 'approve' else 'Từ chối'

        try:
            with transaction.atomic():
                matran.TrangThai = trang_thai_moi

                # BGH set deadline nộp đề khi duyệt
                if action == 'approve' and deadline_nop_str:
                    try:
                        d_nop = date.fromisoformat(deadline_nop_str)
                        if d_nop < date.today():
                            messages.error(request, 'Hạn nộp đề thi không được ở trong quá khứ.')
                            return redirect('matrix_detail', pk=pk)
                        matran.DeadlineNopDe = d_nop
                        matran.DeadlineSuaDe = None  # reset deadline sửa khi duyệt mới
                        matran.NguoiSetDeadline = gv
                        matran.NgaySetDeadline = timezone.now()
                    except ValueError:
                        messages.warning(request, 'Định dạng ngày deadline không hợp lệ, bỏ qua.')

                # BGH set deadline sửa khi từ chối (yêu cầu chỉnh sửa)
                if action == 'reject' and deadline_sua_str:
                    try:
                        d_sua = date.fromisoformat(deadline_sua_str)
                        if d_sua < date.today():
                            messages.error(request, 'Hạn sửa ma trận không được ở trong quá khứ.')
                            return redirect('matrix_detail', pk=pk)
                        matran.DeadlineSuaDe = d_sua
                        matran.NguoiSetDeadline = gv
                        matran.NgaySetDeadline = timezone.now()
                    except ValueError:
                        messages.warning(request, 'Định dạng ngày deadline sửa không hợp lệ, bỏ qua.')

                matran.save()

                if gv:
                    LichSuPheDuyetMaTran.objects.create(
                        MaTran=matran,
                        NguoiPheDuyet=gv,
                        TrangThai=trang_thai_moi,
                        GhiChu=ghi_chu
                    )
                messages.success(request, f'Đã {trang_thai_moi.lower()} ma trận thành công.')
        except Exception as e:
            messages.error(request, f'Lỗi: {str(e)}')

    return redirect('matrix_detail', pk=pk)


@login_required
@khao_thi_required
def matrix_export(request, pk):
    """
    UC 9.5: Xuất ma trận đề thi
    Hỗ trợ định dạng Word (.docx) và Excel (.xls).
    """
    matran = get_object_or_404(MaTran, pk=pk)
    file_format = request.GET.get('format', 'docx').lower()

    # Kiểm tra phân quyền xuất
    gv = getattr(request.user, 'giaovien', None)
    if not request.user.is_superuser:
        if gv:
            # BGH được xuất toàn bộ
            if gv.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
                pass
            # TCM được xuất ma trận của mình hoặc đã duyệt
            elif gv.ChucVu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
                if matran.NguoiTao != gv and matran.TrangThai != 'Đã duyệt':
                    messages.error(request, 'Bạn không có quyền xuất ma trận này.')
                    return redirect('matrix_detail', pk=pk)
            else:
                if matran.TrangThai != 'Đã duyệt':
                    messages.error(request, 'Bạn chỉ có thể xuất ma trận đã được duyệt.')
                    return redirect('matrix_detail', pk=pk)

    # Chuẩn hóa tên file xuất
    mon_name = matran.MonHoc.TenMon if matran.MonHoc else 'Mon'
    khoi_name = matran.Khoi.TenKhoi if matran.Khoi else 'Khoi'
    raw_filename = f"MaTran_{mon_name}_{khoi_name}_{matran.KyThi or 'KyThi'}"
    clean_filename = unicodedata.normalize('NFKD', raw_filename).encode('ascii', 'ignore').decode('ascii')
    clean_filename = clean_filename.replace(' ', '_')

    if file_format in ['docx', 'word']:
        docx_buffer = generate_matrix_docx(matran)
        response = HttpResponse(
            docx_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="{clean_filename}.docx"'
        return response
    else:
        # Xuất Excel (.xls)
        chi_tiet = matran.chi_tiet.all().select_related('MachKienThuc', 'NoiDung')
        context = {
            'matran': matran,
            'chi_tiet': chi_tiet,
        }
        response = render(request, 'matrix/export.html', context)
        response['Content-Type'] = 'application/vnd.ms-excel; charset=utf-8'
        response['Content-Disposition'] = f'attachment; filename="{clean_filename}.xls"'
        return response


@login_required
@khao_thi_required
def matrix_set_deadline(request, pk):
    """
    BGH set/cập nhật deadline nộp đề hoặc deadline sửa cho một ma trận.
    POST params: deadline_type ('nop'|'sua'), deadline_date (YYYY-MM-DD)
    """
    matran = get_object_or_404(MaTran, pk=pk)
    gv = getattr(request.user, 'giaovien', None)

    if not request.user.is_superuser:
        if not gv or gv.ChucVu not in ['Hiệu trưởng', 'Phó hiệu trưởng']:
            messages.error(request, 'Chỉ Ban Giám Hiệu mới có quyền đặt deadline.')
            return redirect('matrix_detail', pk=pk)

    if request.method == 'POST':
        deadline_type = request.POST.get('deadline_type', 'nop')
        deadline_date_str = request.POST.get('deadline_date', '').strip()

        if not deadline_date_str:
            messages.error(request, 'Vui lòng nhập ngày deadline.')
            return redirect('matrix_detail', pk=pk)

        try:
            deadline_date = date.fromisoformat(deadline_date_str)
        except ValueError:
            messages.error(request, 'Định dạng ngày không hợp lệ. Vui lòng dùng định dạng YYYY-MM-DD.')
            return redirect('matrix_detail', pk=pk)

        if deadline_date < date.today():
            messages.error(request, 'Ngày deadline không được ở trong quá khứ.')
            return redirect('matrix_detail', pk=pk)

        if deadline_type == 'sua':
            matran.DeadlineSuaDe = deadline_date
        else:
            matran.DeadlineNopDe = deadline_date

        matran.NguoiSetDeadline = gv
        matran.NgaySetDeadline = timezone.now()
        matran.save(update_fields=[
            'DeadlineNopDe', 'DeadlineSuaDe', 'NguoiSetDeadline', 'NgaySetDeadline'
        ])

        label = 'sửa đề' if deadline_type == 'sua' else 'nộp đề'
        messages.success(request, f'Đã đặt hạn {label}: {deadline_date.strftime("%d/%m/%Y")}.')

    return redirect('matrix_detail', pk=pk)


@login_required
@khao_thi_required
def matrix_set_deadline_gv(request, pk):
    """
    TCM set deadline làm đề cho TẤT CẢ hoặc NHIỀU giáo viên cùng 1 lần,
    sau khi ma trận đã được BGH duyệt.
    Hỗ trợ chọn toàn bộ nhân sự 1 lần và set deadline 1 lần.
    """
    matran = get_object_or_404(MaTran, pk=pk)
    gv = getattr(request.user, 'giaovien', None)

    if not request.user.is_superuser:
        if not gv or gv.ChucVu not in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
            messages.error(request, 'Chỉ Tổ chuyên môn mới có quyền đặt deadline cho giáo viên.')
            return redirect('matrix_detail', pk=pk)

    if matran.TrangThai != 'Đã duyệt':
        messages.error(request, 'Chỉ được đặt deadline sau khi ma trận đã được phê duyệt.')
        return redirect('matrix_detail', pk=pk)

    if request.method == 'POST':
        gv_ids = request.POST.getlist('gv_ids')
        select_all = request.POST.get('select_all') in ['1', 'true', 'on']
        deadline_date_str = request.POST.get('deadline_date', '').strip()
        ghi_chu = request.POST.get('ghi_chu', '').strip()

        if not deadline_date_str:
            messages.error(request, 'Vui lòng chọn ngày hạn chót (deadline).')
            return redirect('matrix_detail', pk=pk)

        try:
            deadline_date = date.fromisoformat(deadline_date_str)
        except ValueError:
            messages.error(request, 'Định dạng ngày không hợp lệ.')
            return redirect('matrix_detail', pk=pk)

        if deadline_date < date.today():
            messages.error(request, 'Hạn chót không được ở trong quá khứ.')
            return redirect('matrix_detail', pk=pk)

        from core.models import GiaoVien as GV_Model
        available_gvs = GV_Model.objects.exclude(
            TrangThai='Dừng hoạt động'
        ).exclude(
            ChucVu__in=['Hiệu trưởng', 'Phó hiệu trưởng', 'Nhân viên văn thư']
        )

        if select_all or 'all' in gv_ids:
            targets = list(available_gvs)
        else:
            single_gv_id = request.POST.get('gv_id')
            if single_gv_id and single_gv_id not in gv_ids:
                gv_ids.append(single_gv_id)

            if not gv_ids:
                messages.error(request, 'Vui lòng chọn ít nhất một nhân sự hoặc bấm Chọn tất cả.')
                return redirect('matrix_detail', pk=pk)

            targets = list(available_gvs.filter(id__in=gv_ids))

        if not targets:
            messages.error(request, 'Không tìm thấy nhân sự phù hợp để giao deadline.')
            return redirect('matrix_detail', pk=pk)

        count = 0
        for target_gv in targets:
            DeadlineGiaoVien.objects.update_or_create(
                MaTran=matran,
                GiaoVien=target_gv,
                defaults={
                    'NguoiSet': gv,
                    'Deadline': deadline_date,
                    'GhiChu': ghi_chu,
                }
            )
            count += 1

        # Tự động đồng bộ thông báo để chuông của giáo viên nhận được tin ngay
        try:
            from core.notification_service import sync_system_notifications
            sync_system_notifications()
        except Exception:
            pass

        messages.success(
            request, 
            f'Đã thiết lập deadline ({deadline_date.strftime("%d/%m/%Y")}) thành công cho {count} nhân sự trong tổ chuyên môn!'
        )

    return redirect('matrix_detail', pk=pk)


@login_required
@khao_thi_required
def matrix_delete_deadline_gv(request, pk, deadline_pk):
    """Xóa deadline của một giáo viên khỏi ma trận (TCM thực hiện)."""
    matran = get_object_or_404(MaTran, pk=pk)
    gv = getattr(request.user, 'giaovien', None)

    if not request.user.is_superuser:
        if not gv or gv.ChucVu not in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
            messages.error(request, 'Không có quyền thực hiện thao tác này.')
            return redirect('matrix_detail', pk=pk)

    if request.method == 'POST':
        dl = get_object_or_404(DeadlineGiaoVien, pk=deadline_pk, MaTran=matran)
        ten_gv = dl.GiaoVien.HoTen
        dl.delete()
        messages.success(request, f'Đã xóa deadline của {ten_gv}.')

    return redirect('matrix_detail', pk=pk)
