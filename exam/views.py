from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.decorators import khao_thi_required
from django.db.models import Q, Max
from django.http import JsonResponse
from .models import DeThi, DeThi_CT, LichSuPheDuyetDeThi
from matrix.models import MaTran
from core.models import NamHoc, Khoi, MonHoc, GiaoVien
from question_bank.models import CauHoi
from .services import ExamGeneratorService
import json
import io
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
try:
    from docx import Document
    from docx.shared import Pt
except ImportError:
    pass # In case python-docx is not installed yet
@login_required
@khao_thi_required
def exam_list(request):
    """ UC 3.4: Tìm kiếm, Lọc, Danh sách đề thi """
    danh_sach = DeThi.objects.exclude(TrangThai='Đã xóa').order_by('-CreatedAt')
    
    # Phân quyền (Business Rules)
    from core.models import GiaoVien
    gv = GiaoVien.objects.filter(user=request.user).first()
    
    if gv:
        # Create Q objects based on the new properties we added
        # Since is_used and is_scheduled_future are properties, we can't use them in DB Q queries directly.
        # So we have to query the related lich_thi in DB
        from django.utils import timezone
        import datetime
        today = timezone.now().date()
        now = timezone.now().time()
        
        q_used = Q(lich_thi__isnull=False) & (
            Q(lich_thi__NgayThi__lt=today) | 
            (Q(lich_thi__NgayThi=today) & Q(lich_thi__GioKetThuc__lt=now))
        )
        
        q_future = Q(lich_thi__isnull=False) & (
            Q(lich_thi__NgayThi__gt=today) | 
            (Q(lich_thi__NgayThi=today) & Q(lich_thi__GioKetThuc__gte=now))
        )
        
        q_mine = Q(NguoiTao=gv)
        
        if gv.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
            # BGH thấy: Đề của mình, Đề đã sử dụng, Đề đã xếp lịch tương lai (VẪN CHO COI), Đề TCM nộp cho mình (Đã nộp, Chính thức)
            danh_sach = danh_sach.filter(
                q_mine | 
                q_used | 
                q_future | 
                Q(TrangThai__in=['Đã nộp', 'Chính thức'])
            ).distinct()
            
        elif gv.ChucVu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
            mon_ids = gv.MonGiangDay.values_list('id', flat=True)
            khoi_ids = gv.KhoiPhuTrach.values_list('id', flat=True)
            
            # TCM thấy: Đề của mình, Đề đã sử dụng, Đề GV nộp (chỉ 'Đã nộp')
            # KHÔNG thấy đề Chính thức chưa được sử dụng (bảo mật)
            # Tự động kế thừa danh sách môn của GVCN thuộc khối phụ trách
            q_da_nop = Q()
            for k_id in khoi_ids:
                gvcn_subjects = GiaoVien.objects.filter(
                    ChucVu='Giáo viên chủ nhiệm'
                ).filter(
                    Q(lophoc__MaKhoi_id=k_id) | 
                    Q(phanconggiangday__MaLop__MaKhoi_id=k_id)
                ).values_list('MonGiangDay__id', flat=True).distinct()
                
                allowed_mon_ids = set(list(mon_ids) + [sid for sid in gvcn_subjects if sid])
                q_da_nop |= Q(Khoi_id=k_id, MonHoc_id__in=allowed_mon_ids)
                
            q_da_nop = (q_da_nop | Q(NguoiDuyet=gv)) & Q(TrangThai='Đã nộp') & ~q_future
            
            danh_sach = danh_sach.filter(
                q_mine | 
                q_used | 
                q_da_nop
            ).distinct()
            
        else:
            # GV thấy: Đề của mình, Đề đã sử dụng
            danh_sach = danh_sach.filter(
                q_mine | 
                q_used
            ).distinct()
            
    # Lọc cơ bản
    tu_khoa = request.GET.get('q', '')
    if tu_khoa: danh_sach = danh_sach.filter(Q(TenDe__icontains=tu_khoa))

    khoi_id = request.GET.get('khoi')
    if khoi_id: danh_sach = danh_sach.filter(Khoi_id=khoi_id)
        
    mon_id = request.GET.get('mon')
    if mon_id: danh_sach = danh_sach.filter(MonHoc_id=mon_id)

    nam_id = request.GET.get('nam')
    if nam_id: danh_sach = danh_sach.filter(NamHoc_id=nam_id)
    
    hoc_ky = request.GET.get('hoc_ky')
    if hoc_ky: danh_sach = danh_sach.filter(HocKy=hoc_ky)
    
    ky_thi = request.GET.get('ky_thi')
    if ky_thi: danh_sach = danh_sach.filter(KyThi=ky_thi)
    
    trang_thai = request.GET.get('trang_thai')
    if trang_thai: danh_sach = danh_sach.filter(TrangThai=trang_thai)
    
    nguoi_tao = request.GET.get('nguoi_tao')
    if nguoi_tao: danh_sach = danh_sach.filter(NguoiTao_id=nguoi_tao)

    from django.core.paginator import Paginator
    paginator = Paginator(danh_sach, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    danh_sach = page_obj

    context = {
        'danh_sach': danh_sach,
        'page_obj': page_obj,
        'tu_khoa': tu_khoa,
        'khoi_list': Khoi.objects.all(),
        'mon_list': MonHoc.objects.filter(TrangThai='Đang hoạt động'),
        'nam_list': NamHoc.objects.all(),
        'gv_list': GiaoVien.objects.all(),
        'today': timezone.now().date(),
    }
    return render(request, 'exam/list.html', context)

@login_required
@khao_thi_required
def exam_wizard_start(request):
    """ UC 3.1: Thêm đề thi (Chọn cấu hình và sinh đề tự động/thủ công) """
    # BGH không được tạo đề thi mới trực tiếp, phải clone từ đề thi đã có
    gv = getattr(request.user, 'giaovien', None)
    if not request.user.is_superuser and gv and gv.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
        messages.error(request, "Ban Giám hiệu không được tạo đề thi mới trực tiếp. Vui lòng tạo bản sao từ đề thi đã có.")
        return redirect('exam_list')

    if request.method == 'POST':
        nam_hoc = request.POST.get('nam_hoc')
        hoc_ky = request.POST.get('hoc_ky')
        ky_thi = request.POST.get('ky_thi')
        mon_hoc = request.POST.get('mon_hoc')
        khoi = request.POST.get('khoi')
        hinh_thuc = request.POST.get('hinh_thuc')
        
        # Kiểm tra đầy đủ thông tin (Exception 10a)
        if not all([nam_hoc, hoc_ky, ky_thi, mon_hoc, khoi, hinh_thuc]):
            messages.error(request, "Vui lòng chọn đầy đủ Năm học, Học kỳ, Kỳ thi, Môn học, Khối và Hình thức.")
            return redirect('exam_wizard_start')
            
        # Tìm ma trận phù hợp (Exception 11b)
        ma_tran = MaTran.objects.filter(
            NamHoc_id=nam_hoc,
            HocKy=hoc_ky,
            KyThi=ky_thi,
            MonHoc_id=mon_hoc,
            Khoi_id=khoi,
            TrangThai='Đã duyệt'
        ).first()
        
        if not ma_tran:
            messages.error(request, "Không tìm thấy ma trận đề phù hợp đã được phê duyệt.")
            return redirect('exam_wizard_start')
            
        config = {
            'nam_hoc': nam_hoc,
            'hoc_ky': hoc_ky,
            'ky_thi': ky_thi,
            'mon_hoc': mon_hoc,
            'khoi': khoi,
            'hinh_thuc': hinh_thuc,
            'ten_de': f"Đề {ky_thi} - {ma_tran.TenMaTran}"
        }
        
        try:
            user_gv = request.user.giaovien
            if hinh_thuc == 'Tự động':
                de_thi = ExamGeneratorService.generate_auto_exam(ma_tran, config, user_gv)
            else:
                de_thi = ExamGeneratorService.generate_manual_exam_shell(ma_tran, config, user_gv)
                
            messages.success(request, "Tạo đề thi thành công! Vui lòng kiểm tra lại cấu trúc.")
            return redirect('exam_editor', pk=de_thi.pk)
            
        except Exception as e:
            # Lỗi ngân hàng câu hỏi (Exception 13a)
            messages.error(request, f"Ngân hàng câu hỏi không đủ hoặc chưa đáp ứng yêu cầu của ma trận đề. ({str(e)})")
            return redirect('exam_wizard_start')
            
    context = {
        'nam_list': NamHoc.objects.all(),
        'mon_list': MonHoc.objects.filter(TrangThai__in=['Đang hoạt động', 'Đang áp dụng']).prefetch_related('KhoiApDung'),
        'khoi_list': Khoi.objects.all(),
    }
    return render(request, 'exam/wizard_step1.html', context)

@login_required
@khao_thi_required
def exam_editor(request, pk):
    """ UC 3.2: Sửa đề thi (Preview / Chỉnh sửa) """
    de_thi = get_object_or_404(DeThi, pk=pk)
    
    # Quyền truy cập đồng bộ với exam_list
    gv_current = getattr(request.user, 'giaovien', None)
    can_view = False
    
    if gv_current:
        is_used = de_thi.is_used
        is_future = de_thi.is_scheduled_future
        
        if de_thi.NguoiTao == gv_current:
            can_view = True
        elif is_used:
            can_view = True
        else:
            if gv_current.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
                if de_thi.TrangThai in ['Đã nộp', 'Chính thức']:
                    can_view = True
            elif gv_current.ChucVu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
                mon_ids = gv_current.MonGiangDay.values_list('id', flat=True)
                khoi_ids = gv_current.KhoiPhuTrach.values_list('id', flat=True)
                # TCM chỉ xem đề 'Đã nộp' (chưa xem đề Chính thức trừ khi đã được sử dụng)
                if gv_current.has_tcm_permission(de_thi.Khoi_id, de_thi.MonHoc_id) and de_thi.TrangThai == 'Đã nộp' and not is_future:
                    can_view = True
                # TCM luôn xem được đề được giao trực tiếp cho mình (NguoiDuyet)
                elif de_thi.NguoiDuyet_id == gv_current.pk and de_thi.TrangThai == 'Đã nộp':
                    can_view = True
                    
    if not can_view:
        messages.error(request, "Bạn không có quyền xem hoặc chỉnh sửa đề thi này.")
        return redirect('exam_list')
        
    is_nguoi_tao = (de_thi.NguoiTao == gv_current)
    
    if request.method == 'GET' and 'added_question_id' in request.GET:
        added_question_id = request.GET.get('added_question_id')
        if added_question_id:
            try:
                if not DeThi_CT.objects.filter(MaDe=de_thi, MaCauHoi_id=added_question_id).exists():
                    last_order = DeThi_CT.objects.filter(MaDe=de_thi).aggregate(Max('ThuTuCau'))['ThuTuCau__max'] or 0
                    
                    diem_so = 1.0
                    q = CauHoi.objects.get(id=added_question_id)
                    if de_thi.MaMaTran:
                        matching_ct_matran = de_thi.MaMaTran.chi_tiet.filter(
                            NoiDung=q.NoiDungKienThuc,
                            MucDo=q.MucDo,
                            LoaiCauHoi=q.HinhThuc
                        ).first()
                        if matching_ct_matran and matching_ct_matran.SoLuongCau > 0:
                            diem_so = round(matching_ct_matran.Diem / matching_ct_matran.SoLuongCau, 2)
                    
                    DeThi_CT.objects.create(
                        MaDe=de_thi,
                        MaCauHoi_id=added_question_id,
                        ThuTuCau=last_order + 1,
                        DiemSo=diem_so
                    )
                    messages.success(request, "Câu hỏi mới đã được tự động thêm vào đề thi.")
                return redirect('exam_editor', pk=pk)
            except Exception:
                pass

    if request.method == 'POST':
        action = request.POST.get('action')
        
        _read_only_actions = ['clone_exam', 'mark_as_read', 'approve_exam', 'reject_exam']
        
        # Chỉ người tạo mới được sửa cấu trúc đề thi (khi còn Nháp)
        if not is_nguoi_tao and action not in _read_only_actions:
            messages.error(request, "Bạn không có quyền chỉnh sửa nội dung đề thi này.")
            return redirect('exam_editor', pk=pk)
            
        # Ngăn chặn các thao tác sửa đổi nếu không phải Nháp (ngoại trừ các action đọc/duyệt/chuyển)
        if de_thi.TrangThai != 'Nháp' and action not in _read_only_actions:
            messages.warning(request, f"Đề thi đang ở trạng thái '{de_thi.TrangThai}', không thể thực hiện thao tác này.")
            return redirect('exam_editor', pk=pk)
            
        if action == 'rename_exam':
            new_name = request.POST.get('ten_de', '').strip()
            if new_name:
                de_thi.TenDe = new_name[:255]
                de_thi.save()
                messages.success(request, "Cập nhật tên đề thi thành công.")
            return redirect('exam_editor', pk=pk)

        elif action == 'delete_question':
            ct_id = request.POST.get('ct_id')
            DeThi_CT.objects.filter(id=ct_id, MaDe=de_thi).delete()
            # Recalculate total score and order
            chi_tiet = de_thi.dethi_ct_set.all().order_by('ThuTuCau')
            for idx, ct in enumerate(chi_tiet, 1):
                ct.ThuTuCau = idx
                ct.save()
            messages.success(request, "Đã xóa câu hỏi khỏi đề thi.")
            
        elif action == 'update_score':
            ct_id = request.POST.get('ct_id')
            new_score = request.POST.get('new_score')
            if new_score:
                new_score = float(new_score)
                ct_to_update = DeThi_CT.objects.filter(id=ct_id, MaDe=de_thi).first()
                if ct_to_update:
                    ct_to_update.DiemSo = new_score
                    ct_to_update.save()
                    
                    # Auto balance other questions in the same matrix criteria
                    if de_thi.MaMaTran:
                        q = ct_to_update.MaCauHoi
                        matching_ct_matran = de_thi.MaMaTran.chi_tiet.filter(
                            NoiDung=q.NoiDungKienThuc,
                            MucDo=q.MucDo,
                            LoaiCauHoi=q.HinhThuc
                        ).first()
                        
                        if matching_ct_matran:
                            # Get all OTHER questions in this criteria
                            other_cts = [
                                x for x in de_thi.dethi_ct_set.all()
                                if x.id != ct_to_update.id and
                                x.MaCauHoi.NoiDungKienThuc == q.NoiDungKienThuc and
                                x.MaCauHoi.MucDo == q.MucDo and
                                x.MaCauHoi.HinhThuc == q.HinhThuc
                            ]
                            
                            if other_cts:
                                remaining_score = matching_ct_matran.Diem - new_score
                                score_per_other = round(remaining_score / len(other_cts), 2)
                                for x in other_cts:
                                    x.DiemSo = score_per_other
                                    x.save()
                                    
                    messages.success(request, "Đã cập nhật điểm số và tự động cân bằng.")
                
        elif action == 'reorder':
            order_data = request.POST.get('order_data')
            if order_data:
                order_list = json.loads(order_data)
                for item in order_list:
                    DeThi_CT.objects.filter(id=item['id'], MaDe=de_thi).update(ThuTuCau=item['order'])
                messages.success(request, "Đã cập nhật thứ tự câu hỏi.")
                
        elif action == 'update_order':
            ct_id = request.POST.get('ct_id')
            new_order_val = request.POST.get('new_order')
            messages.success(request, "Đã cập nhật thứ tự câu hỏi.")
                
        elif action == 'submit_approval':
            chi_tiet = de_thi.dethi_ct_set.all()
            
            # Kiểm tra điểm số <= 0
            if any(ct.DiemSo <= 0 for ct in chi_tiet):
                messages.error(request, "Vui lòng nhập điểm số hợp lệ cho tất cả câu hỏi (> 0).")
                return redirect('exam_editor', pk=pk)
                
            if action == 'submit_approval':
                # Kiểm tra tổng điểm (Exception 6b)
                current_score = sum(ct.DiemSo for ct in chi_tiet)
                
                # So sánh với TongDiem của đề (giá trị hiển thị trên UI)
                if abs(current_score - de_thi.TongDiem) > 0.01:
                    messages.error(request, f"Tổng điểm hiện tại ({current_score}) chưa đúng theo ma trận đề ({de_thi.TongDiem}). Vui lòng kiểm tra và cập nhật trước khi nộp.")
                    return redirect('exam_editor', pk=pk)
                
                # Cũng kiểm tra với ma trận nếu có
                if de_thi.MaMaTran and abs(current_score - de_thi.MaMaTran.TongSoDiem) > 0.01:
                    messages.error(request, f"Tổng điểm ({current_score}) không khớp với tổng điểm ma trận ({de_thi.MaMaTran.TongSoDiem}). Vui lòng kiểm tra lại.")
                    return redirect('exam_editor', pk=pk)
                    
                # Kiểm tra số lượng câu hỏi (Exception 6a)
                if de_thi.MaMaTran:
                    matran_cts = de_thi.MaMaTran.chi_tiet.all()
                    for m_ct in matran_cts:
                        actual_count = chi_tiet.filter(
                            MaCauHoi__NoiDungKienThuc=m_ct.NoiDung,
                            MaCauHoi__MucDo=m_ct.MucDo,
                            MaCauHoi__HinhThuc=m_ct.LoaiCauHoi
                        ).count()
                        if actual_count < m_ct.SoLuongCau:
                            messages.error(request, "Đề thi chưa đủ số lượng câu hỏi theo ma trận đề. Vui lòng bổ sung trước khi gửi phê duyệt.")
                            return redirect('exam_editor', pk=pk)
                            
                # Xác định người phê duyệt
                try:
                    nguoi_gui = GiaoVien.objects.get(user=request.user)
                    approver = None

                    # Luồng 1: Tổ trưởng / Tổ phó → gửi lên toàn bộ BGH (gán người đầu tiên, BGH thấy hết)
                    if nguoi_gui.ChucVu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
                        approver = GiaoVien.objects.filter(
                            ChucVu__in=['Hiệu trưởng', 'Phó hiệu trưởng'],
                            user__isnull=False
                        ).first()

                    # Luồng 2: GV chủ nhiệm / GV bộ môn / bất kỳ ai khác → Tổ trưởng/Tổ phó theo khối/môn có tài khoản hoạt động
                    else:
                        chuc_vu_to = ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']
                        qs_to = GiaoVien.objects.filter(ChucVu__in=chuc_vu_to, user__isnull=False)
                        
                        # 1. Tìm Tổ trưởng phụ trách Khối của đề thi và có quyền đối với môn học đó (dạy hoặc kế thừa)
                        if de_thi.Khoi and de_thi.MonHoc:
                            for candidate in qs_to.filter(ChucVu='Tổ trưởng chuyên môn', KhoiPhuTrach=de_thi.Khoi):
                                if candidate.has_tcm_permission(de_thi.Khoi_id, de_thi.MonHoc_id):
                                    approver = candidate
                                    break
                            
                            # 2. Nếu không có Tổ trưởng, tìm Tổ phó phụ trách Khối và có quyền đối với môn học đó
                            if not approver:
                                for candidate in qs_to.filter(ChucVu='Tổ phó chuyên môn', KhoiPhuTrach=de_thi.Khoi):
                                    if candidate.has_tcm_permission(de_thi.Khoi_id, de_thi.MonHoc_id):
                                        approver = candidate
                                        break
                                
                        # 3. Nếu không tìm được người khớp cả hai, tìm theo Môn học trước
                        if not approver and de_thi.MonHoc:
                            approver = qs_to.filter(
                                MonGiangDay=de_thi.MonHoc,
                                ChucVu='Tổ trưởng chuyên môn'
                            ).first()
                            if not approver:
                                approver = qs_to.filter(
                                    MonGiangDay=de_thi.MonHoc,
                                    ChucVu='Tổ phó chuyên môn'
                                ).first()
                                
                        # 4. Nếu vẫn không được, tìm theo Khối
                        if not approver and de_thi.Khoi:
                            approver = qs_to.filter(
                                KhoiPhuTrach=de_thi.Khoi,
                                ChucVu='Tổ trưởng chuyên môn'
                            ).first()
                            if not approver:
                                approver = qs_to.filter(
                                    KhoiPhuTrach=de_thi.Khoi,
                                    ChucVu='Tổ phó chuyên môn'
                                ).first()
                                
                        # 5. Fallback cuối cùng: bất kỳ Tổ trưởng nào có tài khoản
                        if not approver:
                            approver = qs_to.filter(ChucVu='Tổ trưởng chuyên môn').first()
                    
                    if approver:
                        de_thi.TrangThai = 'Đã nộp'
                        de_thi.NguoiDuyet = approver
                        de_thi.ThoiGianGiaoDuyet = timezone.now()
                        de_thi.TrangThaiDoc = 'Chưa đọc'  # Reset để người duyệt chưa đọc
                        de_thi.NguoiDoc = None
                        de_thi.save()
                        
                        # Kiểm tra tính kịp thời so với Deadline nộp đề của Ma trận
                        ghi_chu_duyet = f'Gửi đến {approver.HoTen} ({approver.ChucVu})'
                        tre_han = False
                        if de_thi.MaMaTran and de_thi.MaMaTran.DeadlineNopDe:
                            if timezone.now().date() > de_thi.MaMaTran.DeadlineNopDe:
                                tre_han = True
                                ghi_chu_duyet += f' [NỘP TRỄ HẠN - Hạn chót: {de_thi.MaMaTran.DeadlineNopDe.strftime("%d/%m/%Y")}]'

                        LichSuPheDuyetDeThi.objects.create(
                            MaDe=de_thi,
                            NguoiThucHien=nguoi_gui,
                            HanhDong='Gửi duyệt',
                            GhiChu=ghi_chu_duyet
                        )
                        if tre_han:
                            messages.warning(request, f"Gửi đề thi phê duyệt thành công, nhưng TRỄ HẠN so với hạn nộp của Ban Giám hiệu ({de_thi.MaMaTran.DeadlineNopDe.strftime('%d/%m/%Y')}).")
                        else:
                            messages.success(request, "Gửi đề thi phê duyệt thành công.")
                    else:
                        messages.error(request, "Không tìm thấy người phê duyệt phù hợp trên hệ thống. Vui lòng liên hệ Admin.")
                        return redirect('exam_editor', pk=pk)
                except Exception as e:
                    messages.error(request, f"Lỗi khi gửi phê duyệt: {str(e)}")
                    return redirect('exam_editor', pk=pk)
            return redirect('exam_list')
            
        elif action == 'cancel_exam':
            # Xóa đề thi nếu hủy
            de_thi.delete()
            messages.success(request, "Đã hủy đề thi và không lưu dữ liệu.")
            return redirect('exam_list')
            
        elif action == 'clone_exam':
            try:
                # Copy DeThi
                old_pk = de_thi.pk
                new_de_thi = DeThi.objects.get(pk=old_pk)
                new_de_thi.pk = None
                new_name = f"Bản sao - {de_thi.TenDe}"
                new_de_thi.TenDe = new_name[:255]
                new_de_thi.NguoiTao = request.user.giaovien
                new_de_thi.TrangThai = 'Nháp'
                new_de_thi.DeGoc = de_thi
                new_de_thi.NguoiDuyet = None
                new_de_thi.ThoiGianGiaoDuyet = None
                new_de_thi.ThoiGianDuyet = None
                new_de_thi.TrangThaiDoc = 'Chưa đọc'  # Reset trạng thái đọc
                new_de_thi.NguoiDoc = None
                new_de_thi.save()
                
                # Copy DeThi_CT
                old_cts = DeThi_CT.objects.filter(MaDe_id=old_pk)
                new_cts = []
                for ct in old_cts:
                    ct.pk = None
                    ct.MaDe = new_de_thi
                    new_cts.append(ct)
                DeThi_CT.objects.bulk_create(new_cts)
                
                messages.success(request, "Tạo bản sao đề thi thành công. Bạn đang ở chế độ chỉnh sửa bản sao.")
                return redirect('exam_editor', pk=new_de_thi.pk)
                
            except Exception as e:
                messages.error(request, f"Lỗi khi tạo bản sao: {str(e)}")
                return redirect('exam_editor', pk=pk)
                
        elif action == 'mark_as_read':
            gv_reader = getattr(request.user, 'giaovien', None)
            
            is_authorized = False
            if gv_reader:
                # 1. Người được phân công trực tiếp
                if gv_reader.pk == de_thi.NguoiDuyet_id:
                    is_authorized = True
                # 2. Nếu đề gửi cho BGH, thì bất kỳ BGH nào cũng được duyệt/đọc
                elif de_thi.NguoiDuyet and de_thi.NguoiDuyet.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng'] and gv_reader.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
                    is_authorized = True
            
            if is_authorized and de_thi.TrangThai == 'Đã nộp' and de_thi.TrangThaiDoc == 'Chưa đọc':
                de_thi.TrangThaiDoc = 'Đã đọc'
                de_thi.NguoiDoc = gv_reader
                # Không ghi đè ThoiGianDuyet — trường đó dành cho phê duyệt chính thức
                de_thi.save()
                
                LichSuPheDuyetDeThi.objects.create(
                    MaDe=de_thi,
                    NguoiThucHien=gv_reader,
                    HanhDong='Đã đọc',
                    GhiChu='Xác nhận đã tiếp nhận và đọc đề thi'
                )
                messages.success(request, "Đã xác nhận đã đọc đề thi.")
            elif gv_reader and de_thi.TrangThaiDoc == 'Đã đọc':
                messages.info(request, "Đề thi này đã được xác nhận đọc trước đó.")
            else:
                messages.error(request, "Bạn không có quyền thực hiện thao tác này.")
            return redirect('exam_editor', pk=pk)


            
        elif action == 'approve_exam':
            # UC 3.9: Phê duyệt chính thức đề thi (BGH) - chỉ trên bản sao
            try:
                giaovien = request.user.giaovien
                # Kiểm tra quyền: Chỉ BGH được duyệt
                if giaovien.ChucVu not in ['Phó hiệu trưởng', 'Hiệu trưởng']:
                    messages.error(request, "Chỉ Ban giám hiệu mới có quyền phê duyệt chính thức đề thi.")
                    return redirect('exam_editor', pk=pk)

                # Kiểm tra: BGH chỉ duyệt đề do mình tạo (đề gốc hoặc bản sao)
                if de_thi.NguoiTao != giaovien:
                    messages.error(request, "Bạn chỉ có thể phê duyệt đề thi do chính mình tạo.")
                    return redirect('exam_editor', pk=pk)

                # Kiểm tra trạng thái phải là Nháp
                if de_thi.TrangThai != 'Nháp':
                    messages.error(request, "Đề thi này không ở trạng thái có thể phê duyệt.")
                    return redirect('exam_editor', pk=pk)

                # Kiểm tra đã có đề Chính thức cùng bộ chưa
                da_ton_tai = DeThi.objects.filter(
                    TrangThai='Chính thức',
                    NamHoc=de_thi.NamHoc,
                    HocKy=de_thi.HocKy,
                    KyThi=de_thi.KyThi,
                    MonHoc=de_thi.MonHoc,
                    Khoi=de_thi.Khoi,
                ).exclude(pk=de_thi.pk).exists()
                if da_ton_tai:
                    messages.error(request, f"Đã có đề Chính thức cho môn {de_thi.MonHoc} - {de_thi.Khoi} kỳ này. Không thể phê duyệt thêm.")
                    return redirect('exam_editor', pk=pk)
                    
                chi_tiet = de_thi.dethi_ct_set.all()
                
                # Kiểm tra điểm số <= 0
                if any(ct.DiemSo <= 0 for ct in chi_tiet):
                    messages.error(request, "Vui lòng nhập điểm số hợp lệ cho tất cả câu hỏi (> 0).")
                    return redirect('exam_editor', pk=pk)
                    
                # Kiểm tra tổng điểm (Exception 6b)
                current_score = sum(ct.DiemSo for ct in chi_tiet)
                if abs(current_score - de_thi.TongDiem) > 0.01:
                    messages.error(request, f"Tổng điểm hiện tại ({current_score}) chưa đúng theo ma trận đề ({de_thi.TongDiem}). Vui lòng kiểm tra trước khi phê duyệt.")
                    return redirect('exam_editor', pk=pk)
                if de_thi.MaMaTran and abs(current_score - de_thi.MaMaTran.TongSoDiem) > 0.01:
                    messages.error(request, f"Tổng điểm ({current_score}) không khớp với tổng điểm ma trận ({de_thi.MaMaTran.TongSoDiem}). Vui lòng kiểm tra lại.")
                    return redirect('exam_editor', pk=pk)
                    
                # Kiểm tra số lượng câu hỏi (Exception 6a)
                if de_thi.MaMaTran:
                    matran_cts = de_thi.MaMaTran.chi_tiet.all()
                    for m_ct in matran_cts:
                        actual_count = chi_tiet.filter(
                            MaCauHoi__NoiDungKienThuc=m_ct.NoiDung,
                            MaCauHoi__MucDo=m_ct.MucDo,
                            MaCauHoi__HinhThuc=m_ct.LoaiCauHoi
                        ).count()
                        if actual_count < m_ct.SoLuongCau:
                            messages.error(request, "Đề thi chưa đủ số lượng câu hỏi theo ma trận đề. Vui lòng bổ sung trước khi phê duyệt.")
                            return redirect('exam_editor', pk=pk)
                
                # Phê duyệt thành công
                de_thi.TrangThai = 'Chính thức'
                de_thi.NguoiDuyet = giaovien
                de_thi.ThoiGianDuyet = timezone.now()
                de_thi.save()
                
                LichSuPheDuyetDeThi.objects.create(
                    MaDe=de_thi,
                    NguoiThucHien=giaovien,
                    HanhDong='Phê duyệt',
                    GhiChu=f'BGH phê duyệt {"bản sao (gốc: " + de_thi.DeGoc.TenDe + ")" if de_thi.DeGoc else "đề thi do BGH trực tiếp tạo"}'
                )
                messages.success(request, "Phê duyệt đề thi thành công.")
                return redirect('exam_editor', pk=pk)
                
            except Exception as e:
                messages.error(request, f"Lỗi khi phê duyệt: {str(e)}")
                return redirect('exam_editor', pk=pk)
                
        elif action == 'add_manual_question':
            cauhoi_id = request.POST.get('cauhoi_id')
            diem_so = request.POST.get('diem_so')
            if cauhoi_id and diem_so:
                # Tìm thứ tự câu cuối cùng
                last_order = DeThi_CT.objects.filter(MaDe=de_thi).aggregate(Max('ThuTuCau'))['ThuTuCau__max'] or 0
                DeThi_CT.objects.create(
                    MaDe=de_thi,
                    MaCauHoi_id=cauhoi_id,
                    ThuTuCau=last_order + 1,
                    DiemSo=float(diem_so)
                )
                messages.success(request, "Đã thêm câu hỏi vào đề thi.")
            return redirect('exam_editor', pk=pk)

        elif action == 'replace_question':
            replace_ct_id = request.POST.get('replace_ct_id')
            cauhoi_id = request.POST.get('cauhoi_id')
            if replace_ct_id and cauhoi_id:
                ct_to_replace = DeThi_CT.objects.filter(id=replace_ct_id, MaDe=de_thi).first()
                if ct_to_replace:
                    ct_to_replace.MaCauHoi_id = cauhoi_id
                    ct_to_replace.save()
                    messages.success(request, "Thay thế câu hỏi thành công.")
            return redirect('exam_editor', pk=pk)
            
            
        return redirect('exam_editor', pk=pk)
        
    chi_tiet = de_thi.dethi_ct_set.all().select_related('MaCauHoi').prefetch_related('MaCauHoi__dap_ans').order_by('ThuTuCau')
    
    # Calculate current total score
    current_score = sum(ct.DiemSo for ct in chi_tiet)
    
    # Calculate matrix progress
    matrix_progress = []
    if de_thi.MaMaTran:
        for ct in de_thi.MaMaTran.chi_tiet.all():
            selected_count = DeThi_CT.objects.filter(
                MaDe=de_thi,
                MaCauHoi__NoiDungKienThuc=ct.NoiDung,
                MaCauHoi__MucDo=ct.MucDo,
                MaCauHoi__HinhThuc=ct.LoaiCauHoi
            ).count()
            
            diem_moi_cau = round(ct.Diem / ct.SoLuongCau, 2) if ct.SoLuongCau > 0 else 0
            
            matrix_progress.append({
                'ct': ct,
                'selected': selected_count,
                'required': ct.SoLuongCau,
                'diem_moi_cau': diem_moi_cau,
                'is_completed': selected_count >= ct.SoLuongCau
            })
    
    # Kiểm tra đã có đề "Chính thức" cùng bộ (NamHoc, HocKy, KyThi, MonHoc, Khoi) chưa
    da_co_chinh_thuc = DeThi.objects.filter(
        TrangThai='Chính thức',
        NamHoc=de_thi.NamHoc,
        HocKy=de_thi.HocKy,
        KyThi=de_thi.KyThi,
        MonHoc=de_thi.MonHoc,
        Khoi=de_thi.Khoi,
    ).exclude(pk=de_thi.pk).exists()

    # Lấy thông tin đọc đề (cho hiển thị "Đọc lúc" chính xác, tránh dùng ThoiGianDuyet nhầm)
    lich_su_da_doc = de_thi.lich_su.filter(HanhDong='Đã đọc').order_by('ThoiGian').first()

    return render(request, 'exam/editor.html', {
        'de_thi': de_thi,
        'chi_tiet': chi_tiet,
        'current_score': current_score,
        'matrix_progress': matrix_progress,
        'da_co_chinh_thuc': da_co_chinh_thuc,
        'lich_su_da_doc': lich_su_da_doc,
    })

@login_required
@khao_thi_required
def api_get_matching_questions(request):
    ct_matran_id = request.GET.get('ct_matran_id')
    replace_ct_id = request.GET.get('replace_ct_id')
    exam_id = request.GET.get('exam_id')
    
    if not exam_id:
        return JsonResponse({'error': 'Thiếu tham số'}, status=400)
        
    try:
        from matrix.models import CT_MaTran
        
        target_noidung = None
        target_muc_do = None
        target_loai_cau_hoi = None
        target_noidung_id = ''
        target_mach_id = ''
        
        if ct_matran_id:
            ct = get_object_or_404(CT_MaTran, pk=ct_matran_id)
            target_noidung = ct.NoiDung
            target_muc_do = ct.MucDo
            target_loai_cau_hoi = ct.LoaiCauHoi
            target_noidung_id = ct.NoiDung_id if ct.NoiDung else ''
            target_mach_id = ct.NoiDung.MachKienThuc_id if ct.NoiDung and getattr(ct.NoiDung, 'MachKienThuc_id', '') else ''
        elif replace_ct_id:
            ct_dethi = get_object_or_404(DeThi_CT, pk=replace_ct_id)
            q = ct_dethi.MaCauHoi
            target_noidung = q.NoiDungKienThuc
            target_muc_do = q.MucDo
            target_loai_cau_hoi = q.HinhThuc
            target_noidung_id = target_noidung.id if target_noidung else ''
            target_mach_id = target_noidung.MachKienThuc_id if target_noidung and getattr(target_noidung, 'MachKienThuc_id', '') else ''
        else:
            return JsonResponse({'error': 'Thiếu tham số ct_matran_id hoặc replace_ct_id'}, status=400)
        
        # Lấy danh sách ID các câu hỏi đã có trong đề thi này
        existing_q_ids = DeThi_CT.objects.filter(MaDe_id=exam_id).values_list('MaCauHoi_id', flat=True)
        
        # Tìm các câu hỏi phù hợp trong ngân hàng (strictly filter by MonHoc and Khoi)
        de_thi = get_object_or_404(DeThi, pk=exam_id)
        cau_hois = CauHoi.objects.filter(
            NoiDungKienThuc=target_noidung,
            MucDo=target_muc_do,
            HinhThuc=target_loai_cau_hoi,
            MonHoc=de_thi.MonHoc,
            Khoi=de_thi.Khoi
        ).exclude(id__in=existing_q_ids).order_by('-id')[:50]
        
        results = []
        for q in cau_hois:
            results.append({
                'id': q.id,
                'noidung': q.NoiDungCauHoi,
                'dang_cau_hoi': q.DangCauHoi,
                'muc_do': q.MucDo,
                'hinh_thuc': q.HinhThuc
            })
            
        return JsonResponse({
            'questions': results,
            'criteria': f"{target_muc_do} - {target_loai_cau_hoi}",
            'ct_info': {
                'muc_do': target_muc_do,
                'hinh_thuc': target_loai_cau_hoi,
                'noidung_id': target_noidung_id,
                'mach_id': target_mach_id
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@khao_thi_required
def exam_delete(request, pk):
    """ UC 3.3: Xóa đề thi (Soft Delete) """
    if request.method == 'POST':
        de_thi = get_object_or_404(DeThi, pk=pk)
        
        if hasattr(request.user, 'giaovien') and de_thi.NguoiTao != request.user.giaovien:
            messages.error(request, "Bạn không có quyền xóa đề thi này.")
            return redirect('exam_list')
            
        if de_thi.TrangThai != 'Nháp':
            messages.warning(request, f"Đề thi đang ở trạng thái '{de_thi.TrangThai}', không thể xóa.")
            return redirect('exam_list')
            
        de_thi.TrangThai = 'Đã xóa'
        de_thi.save()
        messages.success(request, "Xóa đề thi thành công.")
    return redirect('exam_list')

@login_required
@khao_thi_required
def exam_export(request, pk, format):
    """ UC 3.5: Xuất đề thi (PDF, Word) """
    de_thi = get_object_or_404(DeThi, pk=pk)
    # 1. Phân quyền xem và xuất
    if request.user.is_superuser:
        has_permission = True
    else:
        from core.models import GiaoVien
        gv = GiaoVien.objects.filter(user=request.user).first()
        has_permission = False
        if gv:
            if gv.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
                has_permission = True
            elif de_thi.TrangThai == 'Chính thức':
                has_permission = True
            elif gv.ChucVu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
                if de_thi.NguoiTao == gv or de_thi.NguoiDuyet == gv or gv.has_tcm_permission(de_thi.Khoi_id, de_thi.MonHoc_id):
                    has_permission = True
            else:
                mon_ids = gv.MonGiangDay.values_list('id', flat=True)
                if de_thi.NguoiTao == gv or (de_thi.TrangThai == 'Chính thức' and de_thi.MonHoc_id in mon_ids):
                    has_permission = True
    if not has_permission:
        messages.error(request, "Bạn không có quyền xuất đề thi này.")
        return redirect('exam_list')
        
    chi_tiet = de_thi.dethi_ct_set.all().order_by('ThuTuCau')
    
    # Lấy thông tin từ Lịch thi (nếu có)
    from datetime import datetime, date
    thoi_gian = 40
    ngay_thi_str = ""
    try:
        if hasattr(de_thi, 'lich_thi') and de_thi.lich_thi:
            delta = datetime.combine(date.today(), de_thi.lich_thi.GioKetThuc) - datetime.combine(date.today(), de_thi.lich_thi.GioBatDau)
            thoi_gian = delta.seconds // 60
            ngay_thi_str = de_thi.lich_thi.NgayThi.strftime('%d/%m/%Y')
    except:
        pass
    
    # Tạo hoc_ky_text (vd: HỌC KỲ 1 -> HỌC KỲ I)
    hoc_ky_text = (de_thi.HocKy or "").upper().replace("1", "I").replace("2", "II")
    
    from django.utils.html import strip_tags
    is_tieng_viet = (de_thi.MonHoc.TenMon.strip().lower() == 'tiếng việt') if de_thi.MonHoc else False
    
    def process_single_ct(ct):
        noidung_text = strip_tags(ct.MaCauHoi.NoiDungCauHoi).replace('&nbsp;', ' ')
        ans_text = ""
        dap_an_dung = ""
        if ct.MaCauHoi.dap_ans.exists():
            dap_ans = ct.MaCauHoi.dap_ans.all().order_by('ThuTu')
            labels = ['A', 'B', 'C', 'D', 'E', 'F']
            ans_texts = []
            correct_texts = []
            for idx, da in enumerate(dap_ans):
                label = labels[idx] if idx < len(labels) else str(idx+1)
                da_text = strip_tags(da.NoiDung).replace('&nbsp;', ' ')
                ans_texts.append(f"{label}. {da_text}")
                if da.LaDapAnDung:
                    correct_texts.append(f"{label}. {da_text}")
            ans_text = "    ".join(ans_texts)
            dap_an_dung = " ; ".join(correct_texts) if correct_texts else "........................................"
        else:
            dap_an_dung = strip_tags(ct.MaCauHoi.DapAnMau).replace('&nbsp;', ' ') if ct.MaCauHoi.DapAnMau else "........................................"
            
        return {
            'thu_tu': ct.ThuTuCau,
            'diem': ct.DiemSo,
            'noi_dung': noidung_text,
            'dap_ans': ans_text,
            'dap_an_dung': dap_an_dung,
            'cau_hoi': ct.MaCauHoi,
            'noi_dung_html': ct.MaCauHoi.NoiDungCauHoi,
            'hinh_anh_url': ct.MaCauHoi.HinhAnh.path if ct.MaCauHoi.HinhAnh else None
        }

    questions = []
    
    if is_tieng_viet:
        mach_dict = {}
        mach_order = []
        for ct in chi_tiet:
            mach = ct.MaCauHoi.MachKienThuc
            if mach not in mach_dict:
                mach_dict[mach] = []
                mach_order.append(mach)
            mach_dict[mach].append(ct)
            
        alpha_chars = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        mach_idx = 0
        main_cau_so = 1
        
        for mach in mach_order:
            ct_list = mach_dict[mach]
            char = alpha_chars[mach_idx] if mach_idx < len(alpha_chars) else str(mach_idx + 1)
            mach_name = mach.TenMach if mach else 'Khác'
            questions.append({
                'tieu_de': f"{char}. {mach_name}",
                'diem': '', 'noi_dung': '', 'dap_ans': '', 'dap_an_dung': '', 
                'cau_hoi': None, 'noi_dung_html': '', 'hinh_anh_url': None
            })
            mach_idx += 1
            
            processed_groups = set()
            for ct in ct_list:
                if ct.MaCauHoi.NhomCauHoi:
                    nhom = ct.MaCauHoi.NhomCauHoi
                    if nhom.id not in processed_groups:
                        group_cts = [c for c in ct_list if c.MaCauHoi.NhomCauHoi_id == nhom.id]
                        tong_diem_nhom = sum(c.DiemSo for c in group_cts)
                        
                        questions.append({
                            'tieu_de': f"Câu {main_cau_so} ({tong_diem_nhom} điểm).",
                            'noi_dung': strip_tags(nhom.NoiDungChung or '').replace('&nbsp;', ' '),
                            'noi_dung_html': nhom.NoiDungChung or '',
                            'hinh_anh_url': nhom.HinhAnh.path if nhom.HinhAnh else None,
                            'cau_hoi': None, 'dap_ans': '', 'dap_an_dung': ''
                        })
                        
                        sub_idx = 0
                        sub_chars = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
                        for g_ct in group_cts:
                            sub_char = sub_chars[sub_idx] if sub_idx < len(sub_chars) else str(sub_idx+1)
                            q_dict = process_single_ct(g_ct)
                            q_dict['tieu_de'] = f"{sub_char}."
                            questions.append(q_dict)
                            sub_idx += 1
                        processed_groups.add(nhom.id)
                        main_cau_so += 1
                else:
                    if not ct.MaCauHoi.NhomCauHoi_id or ct.MaCauHoi.NhomCauHoi_id not in processed_groups:
                        q_dict = process_single_ct(ct)
                        q_dict['tieu_de'] = f"Câu {main_cau_so} ({ct.DiemSo} điểm)."
                        questions.append(q_dict)
                        main_cau_so += 1
    else:
        main_cau_so = 1
        processed_groups = set()
        for ct in chi_tiet:
            if ct.MaCauHoi.NhomCauHoi:
                nhom = ct.MaCauHoi.NhomCauHoi
                if nhom.id not in processed_groups:
                    group_cts = [c for c in chi_tiet if c.MaCauHoi.NhomCauHoi_id == nhom.id]
                    tong_diem_nhom = sum(c.DiemSo for c in group_cts)
                    questions.append({
                        'tieu_de': f"Câu {main_cau_so} ({tong_diem_nhom} điểm).",
                        'noi_dung': strip_tags(nhom.NoiDungChung or '').replace('&nbsp;', ' '),
                        'noi_dung_html': nhom.NoiDungChung or '',
                        'hinh_anh_url': nhom.HinhAnh.path if nhom.HinhAnh else None,
                        'cau_hoi': None, 'dap_ans': '', 'dap_an_dung': ''
                    })
                    
                    sub_idx = 0
                    sub_chars = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
                    for g_ct in group_cts:
                        sub_char = sub_chars[sub_idx] if sub_idx < len(sub_chars) else str(sub_idx+1)
                        q_dict = process_single_ct(g_ct)
                        q_dict['tieu_de'] = f"{sub_char}."
                        questions.append(q_dict)
                        sub_idx += 1
                    processed_groups.add(nhom.id)
                    main_cau_so += 1
            else:
                if not ct.MaCauHoi.NhomCauHoi_id or ct.MaCauHoi.NhomCauHoi_id not in processed_groups:
                    q_dict = process_single_ct(ct)
                    q_dict['tieu_de'] = f"Câu {main_cau_so} ({ct.DiemSo} điểm)."
                    questions.append(q_dict)
                    main_cau_so += 1

    if format == 'pdf':
        try:
            pdfmetrics.registerFont(TTFont('Times New Roman', 'C:\\Windows\\Fonts\\times.ttf'))
            pdfmetrics.registerFont(TTFont('Times New Roman Bold', 'C:\\Windows\\Fonts\\timesbd.ttf'))
            pdfmetrics.registerFontFamily('Times New Roman', normal='Times New Roman', bold='Times New Roman Bold', italic='Times New Roman', boldItalic='Times New Roman Bold')
            
            template_path = 'exam/export_pdf.html'
            context = {
                'de_thi': de_thi, 
                'questions': questions,
                'thoi_gian': thoi_gian,
                'ngay_thi_str': ngay_thi_str,
                'hoc_ky_text': hoc_ky_text
            }
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="DeThi_{de_thi.pk}.pdf"'
            template = get_template(template_path)
            html = template.render(context)
            pisa_status = pisa.CreatePDF(html, dest=response, encoding='UTF-8')
            if pisa_status.err:
                messages.error(request, f'Lỗi khi tạo PDF: {pisa_status.err}')
                return redirect('exam_list')
            return response
        except Exception as e:
            messages.error(request, f"Lỗi hệ thống khi tạo PDF: {str(e)}")
            return redirect('exam_list')
        
    elif format == 'word':
        try:
            import os
            from django.conf import settings
            from docxtpl import DocxTemplate
            
            # Load template
            template_path = os.path.join(settings.BASE_DIR, 'media', 'templates', 'dethi_template.docx')
            if not os.path.exists(template_path):
                messages.error(request, "Không tìm thấy file template Word (media/templates/dethi_template.docx).")
                return redirect('exam_list')
                
            doc = DocxTemplate(template_path)
            
            ky_thi = de_thi.KyThi.upper() if de_thi.KyThi else ""
            nam_hoc = de_thi.NamHoc.TenNamHoc if de_thi.NamHoc else ""
            mon_hoc = de_thi.MonHoc.TenMon.upper() if de_thi.MonHoc else ""
            
            khoi_text = de_thi.Khoi.TenKhoi.upper() if de_thi.Khoi else ""
            if khoi_text.startswith("KHỐI"):
                khoi_text = khoi_text.replace("KHỐI", "").strip()
            
            context = {
                'ky_thi': ky_thi + ' ' + hoc_ky_text,
                'nam_hoc': nam_hoc,
                'mon_hoc': mon_hoc,
                'khoi': khoi_text,
                'thoi_gian': thoi_gian,
                'ngay_thi_str': ngay_thi_str,
                'lop': '...................',
                'ho_ten': '...................',
                'questions': questions
            }
            
            doc.render(context)
            
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response['Content-Disposition'] = f'attachment; filename="DeThi_{de_thi.pk}.docx"'
            doc.save(response)
            return response
            
        except Exception as e:
            messages.error(request, f"Lỗi xuất Word: {str(e)}")
            return redirect('exam_list')
            
    return redirect('exam_list')
