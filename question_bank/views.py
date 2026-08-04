from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.decorators import khao_thi_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
import json
import docx
from exam.models import DeThi_CT
import google.generativeai as genai
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import mammoth
from bs4 import BeautifulSoup
import base64
from django.core.files.base import ContentFile
import uuid
from .models import CauHoi, DapAn, NhomCauHoi, MachKienThuc, NoiDungKienThuc
from core.models import Khoi, MonHoc, GiaoVien


def serialize_dap_ans(cau_hoi):
    """Chuyển đổi danh sách đáp án của câu hỏi thành JSON để truyền cho template."""
    result = []
    for da in cau_hoi.dap_ans.all().order_by('ThuTu'):
        result.append({
            'id': da.pk,
            'ThuTu': da.ThuTu,
            'NoiDungTrai': da.NoiDungTrai or '',
            'NoiDung': da.NoiDung or '',
            'LaDapAnDung': da.LaDapAnDung,
            'HinhAnh': da.HinhAnh.url if da.HinhAnh else '',
            'HinhAnhTrai': da.HinhAnhTrai.url if da.HinhAnhTrai else '',
        })
    return json.dumps(result, ensure_ascii=False)

@login_required
@khao_thi_required
def api_mon_theo_khoi(request):
    """API: Trả về danh sách môn học theo khối được chọn"""
    khoi_id = request.GET.get('khoi_id')
    if not khoi_id:
        mons = MonHoc.objects.values('id', 'TenMon')
    else:
        mons = MonHoc.objects.filter(KhoiApDung__id=khoi_id).values('id', 'TenMon')
    return JsonResponse(list(mons), safe=False)

@login_required
@khao_thi_required
def api_mach_theo_mon_khoi(request):
    """API: Trả về danh sách mạch kiến thức theo môn + khối"""
    khoi_id = request.GET.get('khoi_id')
    mon_id = request.GET.get('mon_id')
    machs = MachKienThuc.objects.all()
    if khoi_id:
        machs = machs.filter(Khoi_id=khoi_id)
    if mon_id:
        machs = machs.filter(MonHoc_id=mon_id)
    data = list(machs.values('id', 'TenMach'))
    return JsonResponse(data, safe=False)

@login_required
@khao_thi_required
def api_noidung_theo_mach(request):
    """API: Trả về danh sách Nội dung kiến thức theo Mạch kiến thức"""
    mach_id = request.GET.get('mach_id')
    noidungs = NoiDungKienThuc.objects.all()
    if mach_id:
        noidungs = noidungs.filter(MachKienThuc_id=mach_id)
    data = list(noidungs.values('id', 'TenNoidung'))
    return JsonResponse(data, safe=False)

@login_required
def api_noidung_theo_mach(request):
    """API: Trả về danh sách nội dung kiến thức theo mạch kiến thức"""
    mach_id = request.GET.get('mach_id')
    if not mach_id:
        return JsonResponse([], safe=False)
    noidungs = NoiDungKienThuc.objects.filter(MachKienThuc_id=mach_id).values('id', 'TenNoidung')
    return JsonResponse(list(noidungs), safe=False)

@login_required
@khao_thi_required
def question_list(request):
    keyword = request.GET.get('keyword', '')
    khoi_id = request.GET.get('khoi', '')
    mon_id = request.GET.get('mon', '')
    mach_id = request.GET.get('mach', '')
    hinh_thuc = request.GET.get('hinh_thuc', '')
    dang_cau_hoi = request.GET.get('dang_cau_hoi', '')
    muc_do = request.GET.get('muc_do', '')
    noidung_id = request.GET.get('noidung', '')
    
    questions = CauHoi.objects.all().order_by('-id')
    
    if keyword:
        questions = questions.filter(
            Q(NoiDungCauHoi__icontains=keyword) | 
            Q(NhomCauHoi__TenNhom__icontains=keyword)
        )
        
    if khoi_id: questions = questions.filter(Khoi_id=khoi_id)
    if mon_id: questions = questions.filter(MonHoc_id=mon_id)
    if mach_id: questions = questions.filter(MachKienThuc_id=mach_id)
    if hinh_thuc: questions = questions.filter(HinhThuc=hinh_thuc)
    if dang_cau_hoi: questions = questions.filter(DangCauHoi=dang_cau_hoi)
    if muc_do: questions = questions.filter(MucDo=muc_do)
    if noidung_id: questions = questions.filter(NoiDungKienThuc_id=noidung_id)

    # Lấy danh sách môn đã lọc theo khối (nếu có khối được chọn)
    if khoi_id:
        mons_filtered = MonHoc.objects.filter(KhoiApDung__id=khoi_id)
    else:
        mons_filtered = MonHoc.objects.all()

    # Lấy danh sách mạch đã lọc theo môn + khối
    machs_filtered = MachKienThuc.objects.all()
    if khoi_id:
        machs_filtered = machs_filtered.filter(Khoi_id=khoi_id)
    if mon_id:
        machs_filtered = machs_filtered.filter(MonHoc_id=mon_id)
    
    noidungs_filtered = NoiDungKienThuc.objects.all()
    if mach_id:
        noidungs_filtered = noidungs_filtered.filter(MachKienThuc_id=mach_id)

    from django.core.paginator import Paginator
    paginator = Paginator(questions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    questions = page_obj

    # Câu hỏi đã dùng trong đề thi Chính thức → ẩn nút xóa
    locked_ids = set(
        DeThi_CT.objects.filter(MaDe__TrangThai='Chính thức')
        .values_list('MaCauHoi_id', flat=True)
    )

    context = {
        'questions': questions,
        'page_obj': page_obj,
        'khois': Khoi.objects.all(),
        'mons': mons_filtered,
        'machs': machs_filtered,
        'noidungs': noidungs_filtered,
        # Giữ lại giá trị filter để hiển thị đúng selected
        'selected_khoi': khoi_id,
        'selected_mon': mon_id,
        'selected_mach': mach_id,
        'selected_noidung': noidung_id,
        'selected_dang_cau_hoi': dang_cau_hoi,
        'locked_ids': locked_ids,
    }
    return render(request, 'question_bank/list.html', context)


def check_duplicate_question(khoi_id, mon_id, noi_dung, dang, post_data, exclude_id=None):
    from .models import CauHoi
    qs = CauHoi.objects.filter(
        Khoi_id=khoi_id, MonHoc_id=mon_id,
        DangCauHoi=dang, NoiDungCauHoi__iexact=noi_dung.strip()
    )
    if exclude_id: qs = qs.exclude(id=exclude_id)
    if not qs.exists(): return False
    
    submitted_answers = []
    if dang in ['MCQ', 'MSQ']:
        contents = post_data.getlist('ChoiceContent')
        for c in contents:
            submitted_answers.append(c.strip().lower())
    elif dang == 'TF':
        contents = post_data.getlist('TFContent')
        for c in contents:
            submitted_answers.append(c.strip().lower())
    elif dang == 'Matching':
        lefts = post_data.getlist('MatchLeft')
        rights = post_data.getlist('MatchRight')
        for i in range(len(lefts)):
            submitted_answers.append(lefts[i].strip().lower() + '|' + rights[i].strip().lower())
    elif dang == 'FIB':
        fib = post_data.get('DapAnFIB', '')
        for line in fib.split('\n'):
            if line.strip(): submitted_answers.append(line.strip().lower())
    elif dang.startswith('Essay'):
        # For essay, matching the question content is enough
        return True

    for q in qs:
        db_answers = []
        for da in q.dap_ans.all():
            if dang in ['MCQ', 'MSQ', 'TF']: db_answers.append(da.NoiDung.strip().lower())
            elif dang == 'Matching': db_answers.append((da.NoiDungTrai.strip().lower() if da.NoiDungTrai else '') + '|' + da.NoiDung.strip().lower())
            elif dang == 'FIB': db_answers.append(da.NoiDung.strip().lower())
            
        if sorted(submitted_answers) == sorted(db_answers):
            return True
    return False

@login_required
@khao_thi_required
def question_create(request):
    if request.method == 'POST':
        next_url = request.POST.get('next_url') or request.GET.get('next', '')
        
        khoi = request.POST.get('Khoi')
        mon = request.POST.get('MonHoc')
        nd = request.POST.get('NoiDungCauHoi')
        dang = request.POST.get('DangCauHoi')
        if check_duplicate_question(khoi, mon, nd, dang, request.POST):
            messages.error(request, 'Câu hỏi và đáp án đã tồn tại trong ngân hàng.')
            return redirect(request.path + '?next=' + next_url)
            
        try:
            with transaction.atomic():
                q = CauHoi.objects.create(
                    Khoi_id=request.POST.get('Khoi'),
                    MonHoc_id=request.POST.get('MonHoc'),
                    MachKienThuc_id=request.POST.get('MachKienThuc'),
                    NoiDungKienThuc_id=request.POST.get('NoiDungKienThuc'),
                    HinhThuc=request.POST.get('HinhThuc'),
                    DangCauHoi=request.POST.get('DangCauHoi'),
                    MucDo=request.POST.get('MucDo'),
                    NoiDungCauHoi=request.POST.get('NoiDungCauHoi'),
                    HinhAnh=request.FILES.get('HinhAnh'),
                    NguoiTao=request.user.giaovien
                )
                
                dang = q.DangCauHoi
                if dang in ['MCQ', 'MSQ']:
                    contents = request.POST.getlist('ChoiceContent')
                    corrects = request.POST.getlist('IsCorrect') # List of string indices
                    labels = request.POST.getlist('ChoiceLabel')
                    for i, content in enumerate(contents):
                        label = labels[i] if i < len(labels) else chr(65 + i)
                        DapAn.objects.create(
                            CauHoi=q,
                            ThuTu=i,
                            NoiDungTrai=label,
                            NoiDung=content,
                            LaDapAnDung=(str(i) in corrects),
                            HinhAnh=request.FILES.get(f'ChoiceImage_{i}')
                        )
                elif dang == 'TF':
                    q.DapAnMau = request.POST.get('TfLabels', 'Đúng, Sai')
                    q.save()
                    contents = request.POST.getlist('TFContent')
                    indices = request.POST.getlist('TFIndex')
                    for i, idx in enumerate(indices):
                        correct_label = request.POST.get(f'TFCorrect_{idx}')
                        DapAn.objects.create(
                            CauHoi=q, ThuTu=i, NoiDung=contents[i], NoiDungTrai=correct_label, LaDapAnDung=True, HinhAnh=request.FILES.get(f'TFImage_{idx}')
                        )
                elif dang == 'Matching':
                    lefts = request.POST.getlist('MatchLeft')
                    rights = request.POST.getlist('MatchRight')
                    for i in range(len(lefts)):
                        DapAn.objects.create(
                            CauHoi=q, ThuTu=i, NoiDungTrai=lefts[i], NoiDung=rights[i], LaDapAnDung=True,
                            HinhAnhTrai=request.FILES.get(f'MatchImageLeft_{i}'),
                            HinhAnh=request.FILES.get(f'MatchImageRight_{i}')
                        )
                elif dang == 'FIB':
                    fib = request.POST.get('DapAnFIB', '')
                    for i, line in enumerate(fib.split('\n')):
                        if line.strip():
                            DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDung=line.strip(), LaDapAnDung=True)
                elif dang.startswith('Essay'):
                    q.DapAnMau = request.POST.get('DapAnMau')
                    q.save()
                    hinh_anh_da = request.FILES.get('HinhAnhDapAn')
                    if hinh_anh_da:
                        DapAn.objects.create(CauHoi=q, HinhAnh=hinh_anh_da, LaDapAnDung=True)
                
                messages.success(request, 'Thêm câu hỏi thành công.')
                if next_url:
                    separator = '&' if '?' in next_url else '?'
                    next_url = f"{next_url}{separator}added_question_id={q.id}"
                    return redirect(next_url)
                return redirect('question_list')
        except Exception as e:
            messages.error(request, f'Lỗi: {str(e)}')
            
    next_url = request.GET.get('next', '')
    context = {
        'khois': Khoi.objects.all(),
        'mons': MonHoc.objects.all(),
        'machs': MachKienThuc.objects.all().select_related('MonHoc', 'Khoi'),
        'noidungs': NoiDungKienThuc.objects.all().select_related('MachKienThuc'),
        'next_url': next_url,
        'default_khoi': request.GET.get('khoi_id', ''),
        'default_mon': request.GET.get('mon_id', ''),
        'default_mach': request.GET.get('mach_id', ''),
        'default_noidung': request.GET.get('noidung_id', ''),
        'default_hinh_thuc': request.GET.get('hinh_thuc', ''),
        'default_muc_do': request.GET.get('muc_do', ''),
    }
    return render(request, 'question_bank/form.html', context)

@login_required
@khao_thi_required
def question_update(request, pk):
    cau_hoi = get_object_or_404(CauHoi, pk=pk)
    
    # Kiểm tra phân quyền sửa
    gv = request.user.giaovien
    readonly = False
    if cau_hoi.NguoiTao != gv:
        readonly = True
        messages.info(request, 'Bạn đang xem câu hỏi ở chế độ chỉ đọc (Bạn không phải người tạo).')
        
    elif cau_hoi.dethi_ct_set.exists():
        readonly = True
        messages.info(request, 'Bạn đang xem câu hỏi ở chế độ chỉ đọc (Câu hỏi đã được sử dụng trong đề thi).')
        
    if request.method == 'POST':
        if readonly:
            messages.error(request, 'Bạn không có quyền sửa câu hỏi này.')
            return redirect('question_update', pk=pk)
            
        khoi = request.POST.get('Khoi')
        mon = request.POST.get('MonHoc')
        nd = request.POST.get('NoiDungCauHoi')
        dang = request.POST.get('DangCauHoi')
        if check_duplicate_question(khoi, mon, nd, dang, request.POST, exclude_id=cau_hoi.id):
            messages.error(request, 'Câu hỏi và đáp án đã tồn tại trong ngân hàng.')
            return redirect(request.path)
            
        try:
            with transaction.atomic():
                cau_hoi.Khoi_id = request.POST.get('Khoi')
                cau_hoi.MonHoc_id = request.POST.get('MonHoc')
                cau_hoi.MachKienThuc_id = request.POST.get('MachKienThuc')
                cau_hoi.NoiDungKienThuc_id = request.POST.get('NoiDungKienThuc')
                cau_hoi.HinhThuc = request.POST.get('HinhThuc')
                cau_hoi.DangCauHoi = request.POST.get('DangCauHoi')
                cau_hoi.MucDo = request.POST.get('MucDo')
                cau_hoi.NoiDungCauHoi = request.POST.get('NoiDungCauHoi')
                
                if request.FILES.get('HinhAnh'):
                    cau_hoi.HinhAnh = request.FILES.get('HinhAnh')
                elif request.POST.get('XoaHinhAnh'):
                    cau_hoi.HinhAnh = None
                    
                cau_hoi.save()
                
                # Recreate answers
                cau_hoi.dap_ans.all().delete()
                
                dang = cau_hoi.DangCauHoi
                if dang in ['MCQ', 'MSQ']:
                    contents = request.POST.getlist('ChoiceContent')
                    corrects = request.POST.getlist('IsCorrect')
                    labels = request.POST.getlist('ChoiceLabel')
                    for i, content in enumerate(contents):
                        label = labels[i] if i < len(labels) else chr(65 + i)
                        DapAn.objects.create(
                            CauHoi=cau_hoi,
                            ThuTu=i,
                            NoiDungTrai=label,
                            NoiDung=content,
                            LaDapAnDung=(str(i) in corrects),
                            HinhAnh=request.FILES.get(f'ChoiceImage_{i}')
                        )
                elif dang == 'TF':
                    cau_hoi.DapAnMau = request.POST.get('TfLabels', 'Đúng, Sai')
                    cau_hoi.save()
                    contents = request.POST.getlist('TFContent')
                    indices = request.POST.getlist('TFIndex')
                    for i, idx in enumerate(indices):
                        correct_label = request.POST.get(f'TFCorrect_{idx}')
                        DapAn.objects.create(
                            CauHoi=cau_hoi, ThuTu=i, NoiDung=contents[i], NoiDungTrai=correct_label, LaDapAnDung=True, HinhAnh=request.FILES.get(f'TFImage_{idx}')
                        )
                elif dang == 'Matching':
                    lefts = request.POST.getlist('MatchLeft')
                    rights = request.POST.getlist('MatchRight')
                    for i in range(len(lefts)):
                        DapAn.objects.create(
                            CauHoi=cau_hoi, ThuTu=i, NoiDungTrai=lefts[i], NoiDung=rights[i], LaDapAnDung=True,
                            HinhAnhTrai=request.FILES.get(f'MatchImageLeft_{i}'),
                            HinhAnh=request.FILES.get(f'MatchImageRight_{i}')
                        )
                elif dang == 'FIB':
                    fib = request.POST.get('DapAnFIB', '')
                    for i, line in enumerate(fib.split('\n')):
                        if line.strip():
                            DapAn.objects.create(CauHoi=cau_hoi, ThuTu=i, NoiDung=line.strip(), LaDapAnDung=True)
                elif dang.startswith('Essay'):
                    cau_hoi.DapAnMau = request.POST.get('DapAnMau')
                    cau_hoi.save()
                    hinh_anh_da = request.FILES.get('HinhAnhDapAn')
                    if hinh_anh_da:
                        DapAn.objects.create(CauHoi=cau_hoi, HinhAnh=hinh_anh_da, LaDapAnDung=True)
                
                messages.success(request, 'Cập nhật câu hỏi thành công.')
                return redirect('question_list')
        except Exception as e:
            messages.error(request, f'Lỗi: {str(e)}')
        
    context = {
        'cau_hoi': cau_hoi,
        'dap_ans': cau_hoi.dap_ans.all().order_by('ThuTu'),
        'dap_ans_json': serialize_dap_ans(cau_hoi),
        'readonly': readonly,
        'khois': Khoi.objects.all(),
        'mons': MonHoc.objects.all(),
        'machs': MachKienThuc.objects.all().select_related('MonHoc', 'Khoi'),
        'noidungs': NoiDungKienThuc.objects.all().select_related('MachKienThuc'),
        'default_khoi': '',
        'default_mon': '',
        'default_mach': '',
        'default_noidung': '',
        'default_hinh_thuc': '',
        'default_muc_do': '',
    }
    return render(request, 'question_bank/form.html', context)

@login_required
@khao_thi_required
def question_delete(request, pk):
    cau_hoi = get_object_or_404(CauHoi, pk=pk)
    if request.method == 'POST':
        # Kiểm tra nếu đã được sử dụng trong đề thi
        if cau_hoi.dethi_ct_set.exists():
            messages.error(request, 'Không thể xóa câu hỏi đã được sử dụng trong đề thi.')
            return redirect('question_list')
            
        gv = request.user.giaovien
        if cau_hoi.NguoiTao != gv:
            messages.error(request, 'Bạn không có quyền xóa câu hỏi này (chỉ người tạo mới có quyền).')
            return redirect('question_list')
            
        cau_hoi.delete()
        messages.success(request, 'Xóa câu hỏi thành công.')
    return redirect('question_list')

@login_required
@khao_thi_required
def group_create(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                nhom = NhomCauHoi.objects.create(
                    TenNhom=request.POST.get('TenNhom'),
                    Khoi_id=request.POST.get('Khoi'),
                    MonHoc_id=request.POST.get('MonHoc'),
                    MachKienThuc_id=request.POST.get('MachKienThuc'),
                    NoiDungKienThuc_id=request.POST.get('NoiDungKienThuc'),
                    NoiDungChung=request.POST.get('NoiDungChung'),
                    MoTa=request.POST.get('MoTa'),
                    HinhAnh=request.FILES.get('HinhAnh'),
                    NguoiTao=request.user.giaovien
                )
                messages.success(request, 'Tạo nhóm câu hỏi thành công.')
                return redirect('group_update', pk=nhom.pk)
        except Exception as e:
            messages.error(request, f'Lỗi: {str(e)}')
            
    context = {
        'khois': Khoi.objects.all(),
        'mons': MonHoc.objects.all(),
        'machs': MachKienThuc.objects.all(),
        'noidungs': NoiDungKienThuc.objects.all()
    }
    return render(request, 'question_bank/group_form.html', context)

@login_required
@khao_thi_required
def group_update(request, pk):
    nhom = get_object_or_404(NhomCauHoi, pk=pk)
    
    # Kiểm tra phân quyền sửa
    gv = request.user.giaovien
    has_permission = False
    if gv.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
        has_permission = True
    elif gv.ChucVu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
        if nhom.NguoiTao == gv:
            has_permission = True
        else:
            if gv.has_tcm_permission(nhom.Khoi_id, nhom.MonHoc_id):
                has_permission = True
    else:
        if nhom.NguoiTao == gv:
            has_permission = True
            
    if not has_permission:
        messages.error(request, 'Bạn không có quyền sửa nhóm câu hỏi này.')
        return redirect('question_list')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            with transaction.atomic():
                if action == 'add_child':
                    # Add child question
                    q = CauHoi.objects.create(
                        NhomCauHoi=nhom,
                        Khoi=nhom.Khoi,
                        MonHoc=nhom.MonHoc,
                        MachKienThuc=nhom.MachKienThuc,
                        NoiDungKienThuc=nhom.NoiDungKienThuc,
                        HinhThuc=request.POST.get('HinhThuc'),
                        DangCauHoi=request.POST.get('DangCauHoi'),
                        MucDo=request.POST.get('MucDo'),
                        NoiDungCauHoi=request.POST.get('NoiDungCauHoi'),
                        HinhAnh=request.FILES.get('HinhAnh'),
                        NguoiTao=request.user.giaovien
                    )
                    
                    dang = q.DangCauHoi
                    if dang in ['MCQ', 'MSQ']:
                        contents = request.POST.getlist('ChoiceContent')
                        corrects = request.POST.getlist('IsCorrect')
                        labels = request.POST.getlist('ChoiceLabel')
                        for i, content in enumerate(contents):
                            label = labels[i] if i < len(labels) else chr(65 + i)
                            DapAn.objects.create(
                                CauHoi=q, ThuTu=i, NoiDungTrai=label, NoiDung=content, LaDapAnDung=(str(i) in corrects), HinhAnh=request.FILES.get(f'ChoiceImage_{i}')
                            )
                    elif dang == 'TF':
                        q.DapAnMau = request.POST.get('TfLabels', 'Đúng, Sai')
                        q.save()
                        contents = request.POST.getlist('TFContent')
                        indices = request.POST.getlist('TFIndex')
                        for i, idx in enumerate(indices):
                            correct_label = request.POST.get(f'TFCorrect_{idx}')
                            DapAn.objects.create(
                                CauHoi=q, ThuTu=i, NoiDung=contents[i], NoiDungTrai=correct_label, LaDapAnDung=True, HinhAnh=request.FILES.get(f'TFImage_{idx}')
                            )
                    elif dang == 'Matching':
                        lefts = request.POST.getlist('MatchLeft')
                        rights = request.POST.getlist('MatchRight')
                        for i in range(len(lefts)):
                            DapAn.objects.create(
                                CauHoi=q, ThuTu=i, NoiDungTrai=lefts[i], NoiDung=rights[i], LaDapAnDung=True,
                                HinhAnhTrai=request.FILES.get(f'MatchImageLeft_{i}'),
                                HinhAnh=request.FILES.get(f'MatchImageRight_{i}')
                            )
                    elif dang == 'FIB':
                        fib = request.POST.get('DapAnFIB', '')
                        for i, line in enumerate(fib.split('\n')):
                            if line.strip():
                                DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDung=line.strip(), LaDapAnDung=True)
                    elif dang.startswith('Essay'):
                        q.DapAnMau = request.POST.get('DapAnMau')
                        q.save()
                        hinh_anh_da = request.FILES.get('HinhAnhDapAn')
                        if hinh_anh_da:
                            DapAn.objects.create(CauHoi=q, HinhAnh=hinh_anh_da, LaDapAnDung=True)
                            
                    messages.success(request, 'Thêm câu hỏi thành viên thành công.')
                    
                else:
                    # Update group info
                    nhom.TenNhom = request.POST.get('TenNhom')
                    nhom.NoiDungChung = request.POST.get('NoiDungChung')
                    nhom.MoTa = request.POST.get('MoTa')
                    if request.FILES.get('HinhAnh'):
                        nhom.HinhAnh = request.FILES.get('HinhAnh')
                    elif request.POST.get('XoaHinhAnh'):
                        nhom.HinhAnh = None
                    nhom.save()
                    messages.success(request, 'Cập nhật nhóm câu hỏi thành công.')
                    
        except Exception as e:
            messages.error(request, f'Lỗi: {str(e)}')
            
        return redirect('group_update', pk=nhom.pk)
        
    context = {
        'nhom': nhom,
        'cau_hois': nhom.cau_hois.all().order_by('-id'),
        'khois': Khoi.objects.all(),
        'mons': MonHoc.objects.all(),
        'machs': MachKienThuc.objects.all(),
        'noidungs': NoiDungKienThuc.objects.all()
    }
    return render(request, 'question_bank/group_form.html', context)

@login_required
@khao_thi_required
def group_delete(request, pk):
    nhom = get_object_or_404(NhomCauHoi, pk=pk)
    if request.method == 'POST':
        # Kiểm tra sử dụng
        if nhom.cau_hois.filter(dethi_ct__isnull=False).exists():
            messages.error(request, 'Không thể xóa nhóm chứa câu hỏi đã được sử dụng trong đề thi.')
            return redirect('question_list')
            
        gv = request.user.giaovien
        has_permission = False
        if gv.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
            has_permission = True
        elif gv.ChucVu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
            if nhom.NguoiTao == gv:
                has_permission = True
            else:
                if gv.has_tcm_permission(nhom.Khoi_id, nhom.MonHoc_id):
                    has_permission = True
        else: # Giáo viên
            if nhom.NguoiTao == gv:
                has_permission = True
                
        if not has_permission:
            messages.error(request, 'Bạn không có quyền xóa nhóm câu hỏi này.')
            return redirect('question_list')
            
        nhom.delete()
        messages.success(request, 'Xóa nhóm câu hỏi thành công.')
    return redirect('question_list')

@login_required
@khao_thi_required
def import_word_preview(request):
    if request.method == 'POST' and request.FILES.get('word_file'):
        word_file = request.FILES['word_file']
        try:
            file_name = word_file.name.lower()
            if file_name.endswith('.pdf'):
                from pdf2docx import Converter
                import tempfile
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                    for chunk in word_file.chunks():
                        temp_pdf.write(chunk)
                    temp_pdf_path = temp_pdf.name
                    
                temp_docx_path = temp_pdf_path + '.docx'
                
                # Chuyển đổi PDF sang DOCX
                cv = Converter(temp_pdf_path)
                cv.convert(temp_docx_path)
                cv.close()
                
                # Trích xuất DOCX vừa tạo
                with open(temp_docx_path, "rb") as f:
                    result = mammoth.convert_to_html(f)
                    
                os.remove(temp_pdf_path)
                os.remove(temp_docx_path)
            else:
                # Sử dụng mammoth để chuyển Word sang HTML
                result = mammoth.convert_to_html(word_file)
                
            html = result.value
            
            # Tách Base64 ra khỏi HTML để không làm quá tải AI
            soup = BeautifulSoup(html, 'html.parser')
            images_dict = {}
            img_index = 0
            
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and src.startswith('data:image/'):
                    # Chuẩn hóa chuỗi base64 (xóa khoảng trắng, ký tự xuống dòng)
                    src = src.replace('\n', '').replace('\r', '').replace(' ', '')
                    img_id = f"IMAGE_{img_index}"
                    images_dict[img_id] = src
                    img['src'] = img_id
                    img['id'] = img_id
                    img_index += 1
                    
            raw_text = str(soup)
            
            api_key = getattr(settings, 'GEMINI_API_KEY', '')
            if not api_key:
                messages.error(request, 'Cần cấu hình GEMINI_API_KEY trong settings để sử dụng tính năng trích xuất thông minh.')
                return render(request, 'question_bank/import_word.html', {'parsed_groups': '[]'})
                
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-flash-latest')
            
            khois_list = list(Khoi.objects.values('id', 'TenKhoi'))
            mons_list = list(MonHoc.objects.values('id', 'TenMon'))
            machs_list = list(MachKienThuc.objects.values('id', 'TenMach', 'MonHoc_id'))
            noidungs_list = list(NoiDungKienThuc.objects.values('id', 'TenNoidung', 'MachKienThuc_id'))
            
            prompt = f"""
            Bạn là một hệ thống trích xuất và phân loại câu hỏi thông minh từ đề thi.
            Dưới đây là toàn bộ nội dung HTML của đề thi (bao gồm cả đề bài và đáp án/hướng dẫn chấm nếu có):
            
            --- BẮT ĐẦU ĐỀ THI ---
            {raw_text}
            --- KẾT THÚC ĐỀ THI ---
            
            Nhiệm vụ 1: Bóc tách cấu trúc đề thi, đáp án và xác định chính xác DẠNG CÂU HỎI.
            Các dạng câu hỏi được hỗ trợ (chọn 1 cho trường "question_type"):
            - "MCQ": Trắc nghiệm 1 lựa chọn đúng.
            - "MSQ": Trắc nghiệm nhiều lựa chọn đúng.
            - "TF": Trắc nghiệm Đúng/Sai (Gồm nhiều mệnh đề, yêu cầu đánh giá từng mệnh đề là Đúng hay Sai).
            - "Matching": Câu hỏi ghép nối (Nối các mục ở 2 cột với nhau).
            - "FIB": Câu hỏi điền khuyết (Điền từ vào chỗ trống).
            - "EssayShort": Tự luận ngắn (Ví dụ: đặt câu, viết 1 đoạn văn ngắn, tính toán tự luận).
            - "EssayLong": Tự luận dài (Ví dụ: Tập làm văn, viết bài văn).
            Nếu là dạng tự luận, phần giải thích/đáp án/barem điểm phải được gán vào trường "explanation".
            
            LƯU Ý CỰC KỲ QUAN TRỌNG VỀ ĐỊNH DẠNG:
            1. BẠN PHẢI LOẠI BỎ TOÀN BỘ CÁC THẺ HTML (như <br>, <strong>, <p>, <span>...) ra khỏi nội dung câu hỏi và đáp án, CHỈ GIỮ LẠI PLAIN TEXT. Tuyệt đối không được trả về thẻ HTML trong kết quả.
            2. NẾU CÂU HỎI CÓ CÁC LỰA CHỌN ĐÁP ÁN (ví dụ A, B, C, D), BẠN BẮT BUỘC PHẢI TÁCH CHÚNG RA KHỎI NỘI DUNG CÂU HỎI VÀ ĐƯA VÀO MẢNG `answers`. KHÔNG ĐƯỢC GỘP LỰA CHỌN ĐÁP ÁN VÀO TRONG TRƯỜNG `content` CỦA CÂU HỎI.
            3. PHẢI PHÂN LOẠI ĐÚNG DẠNG CÂU HỎI. Nếu câu hỏi có 4 phương án A,B,C,D thì đó là MCQ, không phải tự luận!
            
            LƯU Ý VỀ HÌNH ẢNH: Trong văn bản HTML có các thẻ `<img src="IMAGE_X" id="IMAGE_X">`. 
            - Nếu câu hỏi có chứa hình ảnh, hãy đặt giá trị `IMAGE_X` vào trường `image` của câu hỏi. Nếu không có, để null.
            - Nếu đáp án/phương án có hình ảnh, hãy đặt `IMAGE_X` vào trường `image` (hoặc `left_image`, `right_image` tùy dạng) của phương án đó. Nếu không, để null.
            
            Nhiệm vụ 2: Kiểm duyệt và Giải đề tự động
            - Kiểm duyệt: Phân tích nội dung đề thi. Nếu phát hiện kiến thức VƯỢT QUÁ chương trình Tiểu học (Ví dụ: Toán cấp 2, 3, Đại học, môn học lạ), hãy gán "is_out_of_scope": true và ghi rõ cảnh báo vào "scope_warning" (VD: "Đề thi này chứa kiến thức Đại số cấp 2"). Nếu bình thường, để false và null.
            - Giải đề: Đóng vai trò là Giáo viên, nếu đề thi KHÔNG CÓ SẴN ĐÁP ÁN ở cuối, bạn phải TỰ ĐỘNG GIẢI các câu hỏi và điền đáp án đúng vào cấu trúc. ĐỒNG THỜI, gán cờ "is_ai_solved": true cho các câu hỏi mà bạn phải tự giải. Nếu đề đã có sẵn đáp án, gán false.
            
            Nhiệm vụ 3: Phân loại từng câu hỏi dựa vào danh sách sau (trả về ID tương ứng, nếu không rõ thì null):
            - Khối: {khois_list}
            - Môn học: {mons_list}
            - Mạch kiến thức: {machs_list}
            - Nội dung kiến thức: {noidungs_list}
            
            Yêu cầu bắt buộc: Trả về kết quả dưới định dạng OBJECT JSON gồm các trường:
            - "is_out_of_scope": boolean
            - "scope_warning": string hoặc null
            - "groups": Mảng chứa các nhóm câu hỏi. (Nếu câu hỏi không thuộc đoạn văn nào, hãy để group_content = null).
            
            Cấu trúc mảng `answers` sẽ khác nhau tùy thuộc vào `question_type`:
            - MCQ/MSQ: `answers`: [{{"text": "A. ...", "image": "IMAGE_X"}}], `correct`: 0 (với MCQ) hoặc [0, 2] (với MSQ). Đảm bảo phải có mảng `answers` riêng biệt.
            - TF: `answers`: [{{"statement": "Mệnh đề 1", "image": "IMAGE_X", "correct_label": "Đúng"}}].
            - Matching: `answers`: [{{"left": "Từ 1", "left_image": "IMAGE_X", "right": "Nghĩa 1", "right_image": "IMAGE_Y"}}].
            - FIB: `answers`: ["Đáp án 1", "Đáp án 2"]. (Điền khuyết không hỗ trợ ảnh đáp án)
            - EssayShort/EssayLong: `answers`: [].
            
            Ví dụ định dạng trả về:
            {{
              "is_out_of_scope": false,
              "scope_warning": null,
              "groups": [
                {{
                  "group_content": "VỀ LẠI GÒ CÔNG...",
                  "questions": [
                    {{
                      "question_type": "MCQ",
                      "content": "Câu 1: Địa danh được tả là gì?",
                      "image": null,
                      "answers": [{{"text": "A. Đà Lạt", "image": null}}, {{"text": "B. Gò Công", "image": "IMAGE_1"}}],
                      "correct": 1,
                      "explanation": "Chi tiết trong bài...",
                      "is_ai_solved": true,
                      "khoi_id": 4, "mon_id": 2, "mach_id": 10, "noidung_id": 25,
                      "khoi_name": "Khối 4", "mon_name": "Tiếng Việt", "mach_name": "Đọc hiểu", "noidung_name": ""
                    }},
                    {{
                      "question_type": "TF",
                      "content": "Câu 2: Các nhận định sau đúng hay sai?",
                      "answers": [
                          {{"statement": "Gò Công ở miền Tây", "correct_label": "Đúng"}},
                          {{"statement": "Gò Công có núi cao", "correct_label": "Sai"}}
                      ],
                      "correct": null,
                      "explanation": "",
                      "is_ai_solved": false,
                      "khoi_id": 4, "mon_id": 2, "mach_id": 10, "noidung_id": 25,
                      "khoi_name": "Khối 4", "mon_name": "Tiếng Việt", "mach_name": "Đọc hiểu", "noidung_name": ""
                    }}
                  ]
                }}
              ]
            }}
            Chỉ trả về chuỗi JSON (bắt đầu bằng {{ và kết thúc bằng }}), không kèm giải thích.
            """
            
            prompt_parts = [prompt]
            
            # Đính kèm ảnh thực tế cho Gemini
            import io
            from PIL import Image
            for img_id, b64_str in images_dict.items():
                if b64_str.startswith('data:image/'):
                    try:
                        fmt, imgstr = b64_str.split(';base64,')
                        img_bytes = base64.b64decode(imgstr)
                        img = Image.open(io.BytesIO(img_bytes))
                        # Gắn nhãn ID cho bức ảnh để AI nhận biết
                        prompt_parts.append(f"--- ĐÂY LÀ BỨC ẢNH {img_id} ---")
                        prompt_parts.append(img)
                    except Exception:
                        pass
            
            response = model.generate_content(prompt_parts)
            res_text = response.text.strip()
            if res_text.startswith('```json'):
                res_text = res_text[7:-3]
            elif res_text.startswith('```'):
                res_text = res_text[3:-3]
                
            parsed_data = json.loads(res_text.strip())
            
            # Thay thế mã ảnh thành chuỗi Base64 thực tế để hiển thị
            def replace_image_codes(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if isinstance(v, str) and v in images_dict:
                            obj[k] = images_dict[v]
                        else:
                            replace_image_codes(v)
                elif isinstance(obj, list):
                    for item in obj:
                        replace_image_codes(item)
            
            replace_image_codes(parsed_data)
            
            return render(request, 'question_bank/import_word.html', {
                'parsed_groups': json.dumps(parsed_data)
            })
            
        except Exception as e:
            messages.error(request, f'Lỗi đọc file hoặc AI: {str(e)}')
            
    return render(request, 'question_bank/import_word.html', {
        'parsed_groups': '[]'
    })

@csrf_exempt
@login_required
@khao_thi_required
def api_generate_ai_variations(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            original_q = data.get('question_content', '')
            
            api_key = getattr(settings, 'GEMINI_API_KEY', '')
            if not api_key:
                return JsonResponse({'error': 'Chưa cấu hình API Key cho Gemini AI (GEMINI_API_KEY trong settings).'}, status=400)
                
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"""
            Bạn là một chuyên gia ra đề thi. Hãy tạo ra 1 câu hỏi trắc nghiệm tương tự về mặt kiến thức và độ khó so với câu hỏi gốc dưới đây.
            Câu hỏi gốc: {original_q}
            
            Yêu cầu trả về JSON chuẩn theo định dạng sau, không kèm markdown code block:
            {{
                "content": "Câu X: Nội dung câu hỏi mới",
                "answers": ["A. Đáp án 1", "B. Đáp án 2", "C. Đáp án 3", "D. Đáp án 4"],
                "correct": 0
            }}
            Lưu ý correct là chỉ số của đáp án đúng (0 tương ứng A, 1 tương ứng B, v.v.)
            """
            response = model.generate_content(prompt)
            res_text = response.text.strip()
            if res_text.startswith('```json'):
                res_text = res_text[7:-3]
            elif res_text.startswith('```'):
                res_text = res_text[3:-3]
                
            new_q = json.loads(res_text.strip())
            return JsonResponse({'success': True, 'question': new_q})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid method'}, status=400)

@login_required
@khao_thi_required
def save_imported_questions(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            groups = data.get('groups', [])
            
            if not groups:
                return JsonResponse({'error': 'Không có dữ liệu câu hỏi nào để lưu.'}, status=400)
            
            count = 0
            duplicate_count = 0
            with transaction.atomic():
                for group in groups:
                    group_content = group.get('group_content')
                    nhom_obj = None
                    
                    if group_content and group_content.strip():
                        # Lấy tạm khối môn từ câu hỏi đầu tiên của nhóm nếu có
                        first_q = group.get('questions', [{}])[0]
                        khoi_id = first_q.get('khoi_id')
                        mon_id = first_q.get('mon_id')
                        nhom_obj = NhomCauHoi.objects.create(
                            Khoi_id=khoi_id,
                            MonHoc_id=mon_id,
                            TenNhom="Nhóm trích xuất từ Word",
                            DoanVan=group_content.strip()
                        )
                        
                    for q_data in group.get('questions', []):
                        q_type = q_data.get('question_type', 'MCQ')
                        is_trac_nghiem = q_type in ['MCQ', 'MSQ', 'TF', 'Matching', 'FIB']
                        
                        def get_image_file(b64_str):
                            if b64_str and b64_str.startswith('data:image/'):
                                try:
                                    fmt, imgstr = b64_str.split(';base64,')
                                    ext = fmt.split('/')[-1]
                                    return ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")
                                except Exception:
                                    pass
                            return None

                        content = q_data.get('content', '').strip()
                        khoi_id = q_data.get('khoi_id')
                        mon_id = q_data.get('mon_id')

                        # Kiểm tra câu hỏi trùng lặp (dựa trên Khối, Môn, Nội dung)
                        if CauHoi.objects.filter(
                            Khoi_id=khoi_id,
                            MonHoc_id=mon_id,
                            NoiDungCauHoi__iexact=content
                        ).exists():
                            duplicate_count += 1
                            continue

                        q_img_file = get_image_file(q_data.get('image'))
                        
                        q = CauHoi.objects.create(
                            Khoi_id=khoi_id,
                            MonHoc_id=mon_id,
                            MachKienThuc_id=q_data.get('mach_id'),
                            NoiDungKienThuc_id=q_data.get('noidung_id'),
                            NhomCauHoi=nhom_obj,
                            HinhThuc='Trắc nghiệm' if is_trac_nghiem else 'Tự luận',
                            DangCauHoi=q_type,
                            MucDo='Mức 1', 
                            NoiDungCauHoi=content,
                            HinhAnh=q_img_file,
                            DapAnMau=q_data.get('explanation', ''),
                            NguoiTao=request.user.giaovien
                        )
                        
                        answers = q_data.get('answers', [])
                        
                        if q_type == 'MCQ':
                            try:
                                correct_idx = int(q_data.get('correct', 0))
                            except (ValueError, TypeError):
                                correct_idx = 0
                            for i, ans_obj in enumerate(answers):
                                label = chr(65 + i)
                                content = ans_obj.get('text', '') if isinstance(ans_obj, dict) else ans_obj
                                ans_img = get_image_file(ans_obj.get('image')) if isinstance(ans_obj, dict) else None
                                if content.startswith(f"{label}.") or content.startswith(f"{label})"):
                                    content = content[2:].strip()
                                DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDungTrai=label, NoiDung=content, HinhAnh=ans_img, LaDapAnDung=(i == correct_idx))
                                
                        elif q_type == 'MSQ':
                            corrects = q_data.get('correct', [])
                            if not isinstance(corrects, list):
                                corrects = [corrects]
                            for i, ans_obj in enumerate(answers):
                                label = chr(65 + i)
                                content = ans_obj.get('text', '') if isinstance(ans_obj, dict) else ans_obj
                                ans_img = get_image_file(ans_obj.get('image')) if isinstance(ans_obj, dict) else None
                                if content.startswith(f"{label}.") or content.startswith(f"{label})"):
                                    content = content[2:].strip()
                                DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDungTrai=label, NoiDung=content, HinhAnh=ans_img, LaDapAnDung=(i in corrects))
                                
                        elif q_type == 'TF':
                            labels_set = set()
                            for i, ans_obj in enumerate(answers):
                                stmt = ans_obj.get('statement', '')
                                lbl = ans_obj.get('correct_label', 'Đúng')
                                ans_img = get_image_file(ans_obj.get('image'))
                                labels_set.add(lbl)
                                DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDung=stmt, NoiDungTrai=lbl, HinhAnh=ans_img, LaDapAnDung=True)
                            
                            if labels_set:
                                q.DapAnMau = ", ".join(list(labels_set))
                                q.save()
                                
                        elif q_type == 'Matching':
                            for i, ans_obj in enumerate(answers):
                                left_val = ans_obj.get('left', '')
                                right_val = ans_obj.get('right', '')
                                left_img = get_image_file(ans_obj.get('left_image'))
                                right_img = get_image_file(ans_obj.get('right_image'))
                                DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDungTrai=left_val, NoiDung=right_val, HinhAnhTrai=left_img, HinhAnh=right_img, LaDapAnDung=True)
                                
                        elif q_type == 'FIB':
                            for i, ans_text in enumerate(answers):
                                DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDung=ans_text, LaDapAnDung=True)
                                
                        count += 1
                        
            msg = f'Đã lưu thành công {count} câu hỏi!'
            if duplicate_count > 0:
                msg += f' Đã bỏ qua {duplicate_count} câu hỏi bị trùng lặp.'
            return JsonResponse({'success': True, 'message': msg})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=400)

