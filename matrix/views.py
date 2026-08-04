from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.decorators import khao_thi_required
from django.contrib import messages
import re
from django.db import transaction
from .models import MaTran, CT_MaTran, LichSuPheDuyetMaTran

def validate_matrix_details(mach_ids, noidung_ids, mucdos, loais, soluongs, causos, diems, tyles, action):
    errors = []
    
    if action == 'draft' and len(mach_ids) == 0:
        return []
        
    if len(mach_ids) == 0:
        return ["Vui lòng thêm ít nhất 1 dòng chi tiết ma trận."]
        
    if action == 'draft':
        try:
            [int(s) for s in soluongs if s]
            [float(d) for d in diems if d]
            [float(t) for t in tyles if t]
        except ValueError:
            return ["Dữ liệu số (Số câu, Điểm, Tỷ lệ) không hợp lệ."]
        return []
        
    seen_combinations = set()
    all_causos = set()
    tong_ty_le = 0.0
    tong_diem = 0.0
    tong_so_cau = 0
    
    muc_do_cau = {'Mức 1': 0, 'Mức 2': 0, 'Mức 3': 0}
    muc_do_tyle = {'Mức 1': 0.0, 'Mức 2': 0.0, 'Mức 3': 0.0}
    
    causo_pattern = re.compile(r'^[1-9]\d*(,[1-9]\d*)*$')
    
    for i in range(len(mach_ids)):
        row_num = i + 1
        
        if not mach_ids[i] or not noidung_ids[i] or not mucdos[i] or not loais[i] or not soluongs[i] or not causos[i] or not diems[i] or not tyles[i]:
            errors.append(f"Dòng {row_num}: Thiếu thông tin bắt buộc.")
            continue
            
        try:
            sl = int(soluongs[i])
            diem = float(diems[i])
            tyle = float(tyles[i])
        except ValueError:
            errors.append(f"Dòng {row_num}: Dữ liệu số không hợp lệ.")
            continue
            
        if sl <= 0: errors.append(f"Dòng {row_num}: Số lượng câu phải > 0.")
        if diem <= 0: errors.append(f"Dòng {row_num}: Điểm phải > 0.")
        
        if tyle <= 0 or tyle > 100: errors.append(f"Dòng {row_num}: Tỷ lệ (%) không hợp lệ.")
        
        c = str(causos[i]).strip()
        if not causo_pattern.match(c):
            errors.append(f"Dòng {row_num}: Câu số không hợp lệ (sai định dạng, số âm, hoặc có khoảng trắng).")
        else:
            cau_list = c.split(',')
            if len(cau_list) != sl:
                errors.append(f"Dòng {row_num}: Số lượng câu ({sl}) phải bằng số lượng Câu số đã khai báo ({len(cau_list)}).")
                
            for cau in cau_list:
                if cau in all_causos:
                    errors.append(f"Dòng {row_num}: Câu số {cau} đã tồn tại trong ma trận.")
                else:
                    all_causos.add(cau)
                    
        comb = (mach_ids[i], noidung_ids[i], mucdos[i], loais[i])
        if comb in seen_combinations:
            errors.append(f"Dòng {row_num}: Chi tiết ma trận bị trùng (Mạch, Nội dung, Mức độ, Loại).")
        else:
            seen_combinations.add(comb)
            
        tong_ty_le += tyle
        tong_diem += diem
        tong_so_cau += sl
        
        if mucdos[i] in muc_do_cau:
            muc_do_cau[mucdos[i]] += sl
            muc_do_tyle[mucdos[i]] += tyle
            
    if abs(tong_ty_le - 100.0) > 0.01:
        errors.append(f"Tổng tỷ lệ của ma trận phải bằng 100% (Hiện tại: {tong_ty_le}%).")
        
    if abs(tong_diem - 10.0) > 0.01:
        errors.append(f"Tổng điểm của ma trận phải bằng 10.0 (Hiện tại: {tong_diem}).")
        
    if tong_so_cau > 0:
        for muc in ['Mức 1', 'Mức 2', 'Mức 3']:
            if muc_do_tyle[muc] > 0:
                actual_pct = (muc_do_cau[muc] / tong_so_cau) * 100
                diff = abs(actual_pct - muc_do_tyle[muc])
                if diff > 5.01: 
                    errors.append(f"Tỷ lệ {muc} vượt quá sai lệch cho phép (±5%). Quy định: {muc_do_tyle[muc]}%, Thực tế: {round(actual_pct,2)}%. Vui lòng điều chỉnh.")
                    
    return errors

@login_required
@khao_thi_required
def matrix_list(request):
    from django.db.models import Q
    matrans = MaTran.objects.all().order_by('-NgayCapNhat')
    
    # Phân quyền hiển thị
    if request.user.is_superuser:
        # Admin thấy toàn bộ ma trận
        pass
    else:
        try:
            gv = request.user.giaovien
            if gv.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
                # BGH thấy: Đã duyệt, Nháp của chính mình, Đã nộp (của TCM gửi)
                matrans = matrans.filter(Q(NguoiTao=gv) | Q(TrangThai='Đã duyệt') | Q(TrangThai='Đã nộp'))
            elif gv.ChucVu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
                # TCM thấy: Đã duyệt, Nháp/Đã nộp của chính mình
                matrans = matrans.filter(Q(NguoiTao=gv) | Q(TrangThai='Đã duyệt'))
            else:
                # GV thấy: Chỉ Đã duyệt
                matrans = matrans.filter(TrangThai='Đã duyệt')
        except:
            matrans = matrans.filter(TrangThai='Đã duyệt')
        
    # Filter
    namhoc = request.GET.get('namhoc')
    hocky = request.GET.get('hocky')
    kythi = request.GET.get('kythi')
    monhoc = request.GET.get('monhoc')
    khoi = request.GET.get('khoi')
    search = request.GET.get('search')
    trangthai = request.GET.get('trangthai')
    nguoitao = request.GET.get('nguoitao')
    
    if namhoc: matrans = matrans.filter(NamHoc_id=namhoc)
    if hocky: matrans = matrans.filter(HocKy=hocky)
    if kythi: matrans = matrans.filter(KyThi=kythi)
    if monhoc: matrans = matrans.filter(MonHoc_id=monhoc)
    if khoi: matrans = matrans.filter(Khoi_id=khoi)
    if search: matrans = matrans.filter(TenMaTran__icontains=search)
    if trangthai: matrans = matrans.filter(TrangThai=trangthai)
    if nguoitao: matrans = matrans.filter(NguoiTao_id=nguoitao)
    
    from core.models import NamHoc, Khoi, MonHoc, GiaoVien
    from django.core.paginator import Paginator
    paginator = Paginator(matrans, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    matrans = page_obj

    context = {
        'matrans': matrans,
        'page_obj': page_obj,
        'namhocs': NamHoc.objects.all(),
        'khois': Khoi.objects.all(),
        'monhocs': MonHoc.objects.all(),
        'giaoviens': GiaoVien.objects.all(),
    }
    return render(request, 'matrix/list.html', context)

@login_required
@khao_thi_required
def matrix_create(request):
    if request.user.is_superuser:
        messages.error(request, 'Admin không được phép tạo ma trận đề thi.')
        return redirect('matrix_list')
        
    try:
        gv = request.user.giaovien
        if gv.ChucVu not in ['Hiệu trưởng', 'Phó hiệu trưởng', 'Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
            messages.error(request, 'Giáo viên không có quyền tạo ma trận đề thi.')
            return redirect('matrix_list')
    except:
        messages.error(request, 'Tài khoản không hợp lệ để tạo ma trận.')
        return redirect('matrix_list')
        
    from core.models import NamHoc, Khoi, MonHoc
    from question_bank.models import MachKienThuc, NoiDungKienThuc
    
    context = {
        'namhocs': NamHoc.objects.all(),
        'khois': Khoi.objects.all(),
        'monhocs': MonHoc.objects.all(),
        'machs': MachKienThuc.objects.all(),
        'noidungs': NoiDungKienThuc.objects.all(),
    }
    
    if request.method == 'POST':
        from django.db import transaction, IntegrityError
        from core.models import GiaoVien
        action = request.POST.get('action')
        
        ten_matran = request.POST.get('TenMaTran')
        nam_hoc_id = request.POST.get('NamHoc')
        hoc_ky = request.POST.get('HocKy')
        ky_thi = request.POST.get('KyThi')
        khoi_id = request.POST.get('Khoi')
        mon_hoc_id = request.POST.get('MonHoc')
        mo_ta = request.POST.get('MoTa')
        
        mach_ids = request.POST.getlist('MachKienThuc[]')
        noidung_ids = request.POST.getlist('NoiDung[]')
        mucdos = request.POST.getlist('MucDo[]')
        loais = request.POST.getlist('LoaiCauHoi[]')
        soluongs = request.POST.getlist('SoLuongCau[]')
        causos = request.POST.getlist('CauSo[]')
        diems = request.POST.getlist('Diem[]')
        tyles = request.POST.getlist('TyLe[]')
        
        def get_posted_context():
            matran_mock = MaTran(
                TenMaTran=ten_matran, NamHoc_id=nam_hoc_id, HocKy=hoc_ky,
                KyThi=ky_thi, Khoi_id=khoi_id, MonHoc_id=mon_hoc_id, MoTa=mo_ta
            )
            posted_details = []
            for i in range(len(mach_ids)):
                posted_details.append({
                    'MachKienThuc_id': int(mach_ids[i]) if mach_ids[i] else None,
                    'NoiDung_id': int(noidung_ids[i]) if noidung_ids[i] else None,
                    'MucDo': mucdos[i] if i < len(mucdos) else '',
                    'LoaiCauHoi': loais[i] if i < len(loais) else '',
                    'SoLuongCau': soluongs[i] if i < len(soluongs) else '',
                    'CauSo': causos[i] if i < len(causos) else '',
                    'Diem': diems[i] if i < len(diems) else '',
                    'TyLe': tyles[i] if i < len(tyles) else ''
                })
            context['matran'] = matran_mock
            context['posted_details'] = posted_details
            context['is_post_back'] = True
            return context

        detail_errors = validate_matrix_details(mach_ids, noidung_ids, mucdos, loais, soluongs, causos, diems, tyles, action)
        if detail_errors:
            for err in detail_errors:
                messages.error(request, err)
            return render(request, 'matrix/form.html', get_posted_context())
            
        tong_so_cau = sum([int(s) for s in soluongs if s])
        tong_diem = sum([float(d) for d in diems if d])
                
        trang_thai = 'Chờ duyệt' if action == 'submit' else 'Nháp'
        
        try:
            with transaction.atomic():
                gv = GiaoVien.objects.filter(user=request.user).first()
                if not gv:
                    raise Exception('Tài khoản của bạn chưa được liên kết với Giáo viên.')
                    
                if MaTran.objects.filter(NamHoc_id=nam_hoc_id, HocKy=hoc_ky, KyThi=ky_thi, Khoi_id=khoi_id, MonHoc_id=mon_hoc_id).exists():
                    raise IntegrityError('Ma trận cho Học kỳ, Kỳ thi, Khối và Môn học này đã tồn tại!')
                    
                matran = MaTran.objects.create(
                    NguoiTao=gv,
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
                
                for i in range(len(mach_ids)):
                    if mach_ids[i] and noidung_ids[i]:
                        CT_MaTran.objects.create(
                            MaTran=matran,
                            MachKienThuc_id=mach_ids[i],
                            NoiDung_id=noidung_ids[i],
                            MucDo=mucdos[i],
                            LoaiCauHoi=loais[i],
                            SoLuongCau=soluongs[i],
                            CauSo=causos[i],
                            Diem=diems[i],
                            TyLe=tyles[i]
                        )
                
                msg = 'Đã gửi duyệt ma trận thành công.' if action == 'submit' else 'Lưu nháp ma trận thành công.'
                messages.success(request, msg)
                return redirect('matrix_list')
                
        except IntegrityError as e:
            messages.error(request, str(e))
            return render(request, 'matrix/form.html', get_posted_context())
        except Exception as e:
            messages.error(request, f'Lỗi: {str(e)}')
            return render(request, 'matrix/form.html', get_posted_context())
        
    return render(request, 'matrix/form.html', context)

@login_required
@khao_thi_required
def matrix_update(request, pk):
    matran = get_object_or_404(MaTran, pk=pk)
    
    # Kiểm tra phân quyền sửa (Chỉ người tạo và trạng thái Nháp mới được sửa)
    gv = getattr(request.user, 'giaovien', None)
    if matran.NguoiTao != gv:
        messages.error(request, 'Bạn không có quyền sửa ma trận của người khác.')
        return redirect('matrix_list')
        
    if matran.TrangThai != 'Nháp':
        messages.error(request, 'Bạn chỉ có thể sửa ma trận khi đang ở trạng thái Nháp.')
        return redirect('matrix_list')
    
    from core.models import NamHoc, Khoi, MonHoc
    from question_bank.models import MachKienThuc, NoiDungKienThuc
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
        from django.db import transaction, IntegrityError
        action = request.POST.get('action')
        
        has_details = matran.chi_tiet.exists()
        
        new_ten = request.POST.get('TenMaTran')
        new_nam = request.POST.get('NamHoc')
        new_hocky = request.POST.get('HocKy')
        new_kythi = request.POST.get('KyThi')
        new_khoi = request.POST.get('Khoi')
        new_mon = request.POST.get('MonHoc')
        
        if has_details:
            changed = False
            if new_ten and new_ten != matran.TenMaTran: changed = True
            if new_nam and new_nam != str(matran.NamHoc_id): changed = True
            if new_hocky and new_hocky != matran.HocKy: changed = True
            if new_kythi and new_kythi != matran.KyThi: changed = True
            if new_khoi and new_khoi != str(matran.Khoi_id): changed = True
            if new_mon and new_mon != str(matran.MonHoc_id): changed = True
            
            if changed:
                messages.error(request, "Không thể chỉnh sửa thông tin chung khi ma trận đã có chi tiết. Vui lòng xóa toàn bộ chi tiết ma trận trước khi thay đổi.")
                return render(request, 'matrix/form.html', context)
        else:
            matran.TenMaTran = new_ten
            matran.NamHoc_id = new_nam
            matran.HocKy = new_hocky
            matran.KyThi = new_kythi
            matran.Khoi_id = new_khoi
            matran.MonHoc_id = new_mon
            
        matran.MoTa = request.POST.get('MoTa')
        
        mach_ids = request.POST.getlist('MachKienThuc[]')
        noidung_ids = request.POST.getlist('NoiDung[]')
        mucdos = request.POST.getlist('MucDo[]')
        loais = request.POST.getlist('LoaiCauHoi[]')
        soluongs = request.POST.getlist('SoLuongCau[]')
        causos = request.POST.getlist('CauSo[]')
        diems = request.POST.getlist('Diem[]')
        tyles = request.POST.getlist('TyLe[]')
        
        def get_posted_context_update():
            posted_details = []
            for i in range(len(mach_ids)):
                posted_details.append({
                    'MachKienThuc_id': int(mach_ids[i]) if mach_ids[i] else None,
                    'NoiDung_id': int(noidung_ids[i]) if noidung_ids[i] else None,
                    'MucDo': mucdos[i] if i < len(mucdos) else '',
                    'LoaiCauHoi': loais[i] if i < len(loais) else '',
                    'SoLuongCau': soluongs[i] if i < len(soluongs) else '',
                    'CauSo': causos[i] if i < len(causos) else '',
                    'Diem': diems[i] if i < len(diems) else '',
                    'TyLe': tyles[i] if i < len(tyles) else ''
                })
            context['posted_details'] = posted_details
            context['is_post_back'] = True
            return context

        detail_errors = validate_matrix_details(mach_ids, noidung_ids, mucdos, loais, soluongs, causos, diems, tyles, action)
        if detail_errors:
            for err in detail_errors:
                messages.error(request, err)
            return render(request, 'matrix/form.html', get_posted_context_update())
            
        tong_so_cau = sum([int(s) for s in soluongs if s])
        tong_diem = sum([float(d) for d in diems if d])
                
        matran.TrangThai = 'Chờ duyệt' if action == 'submit' else 'Nháp'
        matran.TongSoCau = tong_so_cau
        matran.TongSoDiem = tong_diem
        
        try:
            with transaction.atomic():
                if MaTran.objects.filter(NamHoc_id=matran.NamHoc_id, HocKy=matran.HocKy, KyThi=matran.KyThi, Khoi_id=matran.Khoi_id, MonHoc_id=matran.MonHoc_id).exclude(pk=matran.pk).exists():
                    raise IntegrityError('Ma trận cho Học kỳ, Kỳ thi, Khối và Môn học này đã tồn tại!')
                    
                matran.save()
                
                # Delete old details
                CT_MaTran.objects.filter(MaTran=matran).delete()
                
                # Insert new details
                for i in range(len(mach_ids)):
                    if mach_ids[i] and noidung_ids[i]:
                        CT_MaTran.objects.create(
                            MaTran=matran,
                            MachKienThuc_id=mach_ids[i],
                            NoiDung_id=noidung_ids[i],
                            MucDo=mucdos[i],
                            LoaiCauHoi=loais[i],
                            SoLuongCau=soluongs[i],
                            CauSo=causos[i],
                            Diem=diems[i],
                            TyLe=tyles[i]
                        )
                
                msg = 'Đã gửi duyệt ma trận thành công.' if action == 'submit' else 'Lưu nháp ma trận thành công.'
                messages.success(request, msg)
                return redirect('matrix_list')
                
        except IntegrityError as e:
            messages.error(request, str(e))
            return render(request, 'matrix/form.html', get_posted_context_update())
        except Exception as e:
            messages.error(request, f'Lỗi: {str(e)}')
            return render(request, 'matrix/form.html', get_posted_context_update())
        
    return render(request, 'matrix/form.html', context)

@login_required
@khao_thi_required
def matrix_detail(request, pk):
    matran = get_object_or_404(MaTran, pk=pk)
    chi_tiet = matran.chi_tiet.all()
    
    is_bgh = False
    if hasattr(request.user, 'giaovien'):
        if request.user.giaovien.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
            is_bgh = True
            
    lich_su = matran.lich_su.all().order_by('-ThoiGian')
            
    context = {
        'matran': matran,
        'chi_tiet': chi_tiet,
        'is_bgh': is_bgh,
        'lich_su': lich_su
    }
    return render(request, 'matrix/detail.html', context)

@login_required
@khao_thi_required
def matrix_approve(request, pk):
    matran = get_object_or_404(MaTran, pk=pk)
    
    if request.method == 'POST':
        if not hasattr(request.user, 'giaovien') or request.user.giaovien.ChucVu not in ['Hiệu trưởng', 'Phó hiệu trưởng']:
            messages.error(request, 'Chỉ Ban Giám Hiệu mới có quyền phê duyệt.')
            return redirect('matrix_detail', pk=pk)
            
        action = request.POST.get('action')
        ghi_chu = request.POST.get('GhiChu', '')
        
        trang_thai_moi = 'Đã duyệt' if action == 'approve' else 'Từ chối'
        
        try:
            with transaction.atomic():
                matran.TrangThai = trang_thai_moi
                matran.save()
                
                LichSuPheDuyetMaTran.objects.create(
                    MaTran=matran,
                    NguoiPheDuyet=request.user.giaovien,
                    TrangThai=trang_thai_moi,
                    GhiChu=ghi_chu
                )
                messages.success(request, f'Đã {trang_thai_moi.lower()} ma trận.')
        except Exception as e:
            messages.error(request, f'Lỗi: {str(e)}')
            
    return redirect('matrix_detail', pk=pk)

@login_required
@khao_thi_required
def matrix_export(request, pk):
    matran = get_object_or_404(MaTran, pk=pk)
    chi_tiet = matran.chi_tiet.all()
    
    context = {
        'matran': matran,
        'chi_tiet': chi_tiet,
    }
    
    response = render(request, 'matrix/export.html', context)
    
    filename = f"MaTran_{matran.MonHoc.TenMon if matran.MonHoc else 'Unknown'}_{matran.Khoi.TenKhoi if matran.Khoi else 'Unknown'}.xls"
    import unicodedata
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    filename = filename.replace(' ', '_')
    
    response['Content-Type'] = 'application/vnd.ms-excel; charset=utf-8'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
@khao_thi_required
def matrix_delete(request, pk):
    matran = get_object_or_404(MaTran, pk=pk)
    if request.method == 'POST':
        # Kiểm tra phân quyền xóa (Chỉ người tạo và trạng thái Nháp)
        gv = getattr(request.user, 'giaovien', None)
        if matran.NguoiTao != gv:
            messages.error(request, 'Bạn không có quyền xóa ma trận của người khác.')
            return redirect('matrix_list')
            
        if matran.TrangThai != 'Nháp':
            messages.error(request, 'Chỉ có thể xóa ma trận ở trạng thái Nháp.')
        else:
            matran.delete()
            messages.success(request, 'Xóa ma trận thành công.')
    return redirect('matrix_list')
