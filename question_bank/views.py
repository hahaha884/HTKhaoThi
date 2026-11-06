from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.decorators import khao_thi_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
import json
import os
import docx
from exam.models import DeThi_CT
from groq import Groq
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import mammoth
from bs4 import BeautifulSoup
import base64
from django.core.files.base import ContentFile
import uuid
from .models import CauHoi, DapAn, NhomCauHoi, MachKienThuc, NoiDungKienThuc
from core.models import Khoi, MonHoc, GiaoVien


def call_groq_chat(groq_client, messages, temperature=0.5, max_tokens=2048, model=None, **kwargs):
    """Gọi Groq chat completion với fallback model an toàn."""
    preferred_model = model or getattr(settings, 'GROQ_MODEL', 'openai/gpt-oss-120b')
    models_to_try = [preferred_model, 'openai/gpt-oss-120b', 'qwen/qwen3.8-27b', 'openai/gpt-oss-20b']
    seen = set()
    models_list = []
    for m in models_to_try:
        if m and m not in seen:
            seen.add(m)
            models_list.append(m)

    last_err = None
    for model in models_list:
        try:
            return groq_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if 'model_not_found' in err_str or 'does not exist' in err_str:
                continue
            raise e
    raise last_err


def extract_json_from_ai(res_text):
    """Trích xuất và parse JSON từ chuỗi kết quả của AI."""
    text = res_text.strip()
    if '```json' in text:
        text = text.split('```json', 1)[1].split('```', 1)[0].strip()
    elif '```' in text:
        text = text.split('```', 1)[1].split('```', 1)[0].strip()
    else:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end+1].strip()
    return json.loads(text)


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
    nguoi_tao_id = request.GET.get('nguoi_tao', '')
    
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
    if nguoi_tao_id: questions = questions.filter(NguoiTao_id=nguoi_tao_id)

    # Danh sách người tạo thực tế (giáo viên đã tạo câu hỏi)
    creator_ids = CauHoi.objects.values_list('NguoiTao_id', flat=True).distinct()
    giaoviens = GiaoVien.objects.filter(id__in=creator_ids).order_by('HoTen')

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
        'selected_nguoi_tao': nguoi_tao_id,
        'giaoviens': giaoviens,
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
                        left_val = lefts[i].strip() if i < len(lefts) else ''
                        right_val = rights[i].strip() if i < len(rights) else ''
                        if not left_val and not right_val and not request.FILES.get(f'MatchImageLeft_{i}') and not request.FILES.get(f'MatchImageRight_{i}'):
                            continue
                        DapAn.objects.create(
                            CauHoi=q, ThuTu=i, NoiDungTrai=left_val, NoiDung=right_val, LaDapAnDung=True,
                            HinhAnhTrai=request.FILES.get(f'MatchImageLeft_{i}'),
                            HinhAnh=request.FILES.get(f'MatchImageRight_{i}')
                        )
                elif dang == 'FIB':
                    fib_answers = request.POST.getlist('FIBAnswer')
                    if fib_answers:
                        valid_answers = [ans.strip() for ans in fib_answers if ans.strip()]
                    else:
                        fib = request.POST.get('DapAnFIB', '')
                        valid_answers = [line.strip() for line in fib.splitlines() if line.strip()]
                    for i, ans in enumerate(valid_answers):
                        DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDung=ans, LaDapAnDung=True)
                elif dang.startswith('Essay'):
                    q.DapAnMau = request.POST.get('DapAnMau')
                    q.save()
                    hinh_anh_da = request.FILES.get('HinhAnhDapAn')
                    if hinh_anh_da:
                        DapAn.objects.create(CauHoi=q, HinhAnh=hinh_anh_da, LaDapAnDung=True)
                
                messages.success(request, 'Thêm câu hỏi thành công.')
                is_popup = request.GET.get('popup') == '1' or request.POST.get('popup') == '1'
                if is_popup:
                    html = f"""
                    <script>
                        window.parent.postMessage({{
                            type: 'question_created',
                            added_question_id: {q.id}
                        }}, '*');
                    </script>
                    """
                    from django.http import HttpResponse
                    return HttpResponse(html)
                    
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
        'is_popup': request.GET.get('popup') == '1',
        'is_from_exam': request.GET.get('is_from_exam') == '1',
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
                    old_img_lefts = request.POST.getlist('ExistingMatchImageLeft')
                    old_img_rights = request.POST.getlist('ExistingMatchImageRight')
                    for i in range(len(lefts)):
                        left_val = lefts[i].strip() if i < len(lefts) else ''
                        right_val = rights[i].strip() if i < len(rights) else ''
                        if not left_val and not right_val and not request.FILES.get(f'MatchImageLeft_{i}') and not request.FILES.get(f'MatchImageRight_{i}'):
                            continue
                        new_img_l = request.FILES.get(f'MatchImageLeft_{i}')
                        new_img_r = request.FILES.get(f'MatchImageRight_{i}')
                        da = DapAn.objects.create(
                            CauHoi=cau_hoi, ThuTu=i, NoiDungTrai=left_val, NoiDung=right_val, LaDapAnDung=True,
                            HinhAnhTrai=new_img_l,
                            HinhAnh=new_img_r
                        )
                        if not new_img_l and i < len(old_img_lefts) and old_img_lefts[i]:
                            raw_path = old_img_lefts[i].replace('/media/', '')
                            if raw_path:
                                da.HinhAnhTrai.name = raw_path
                                da.save(update_fields=['HinhAnhTrai'])
                        if not new_img_r and i < len(old_img_rights) and old_img_rights[i]:
                            raw_path = old_img_rights[i].replace('/media/', '')
                            if raw_path:
                                da.HinhAnh.name = raw_path
                                da.save(update_fields=['HinhAnh'])
                elif dang == 'FIB':
                    fib_answers = request.POST.getlist('FIBAnswer')
                    if fib_answers:
                        valid_answers = [ans.strip() for ans in fib_answers if ans.strip()]
                    else:
                        fib = request.POST.get('DapAnFIB', '')
                        valid_answers = [line.strip() for line in fib.splitlines() if line.strip()]
                    for i, ans in enumerate(valid_answers):
                        DapAn.objects.create(CauHoi=cau_hoi, ThuTu=i, NoiDung=ans, LaDapAnDung=True)
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
    khois = Khoi.objects.all().order_by('id')
    mons = MonHoc.objects.all().order_by('id')
    khois_list = list(Khoi.objects.values('id', 'TenKhoi'))
    mons_list = list(MonHoc.objects.values('id', 'TenMon'))
    machs_list = list(MachKienThuc.objects.values('id', 'TenMach', 'MonHoc_id', 'Khoi_id'))
    noidungs_list = list(NoiDungKienThuc.objects.values('id', 'TenNoidung', 'MachKienThuc_id'))

    selected_khoi_id = request.POST.get('khoi_id') or request.GET.get('khoi')
    selected_mon_id = request.POST.get('mon_id') or request.GET.get('mon')
    selected_mach_id = request.POST.get('mach_id') or request.GET.get('mach')

    context_base = {
        'parsed_groups': '[]',
        'khois': khois,
        'mons': mons,
        'khois_data': json.dumps(khois_list),
        'mons_data': json.dumps(mons_list),
        'machs_data': json.dumps(machs_list),
        'noidungs_data': json.dumps(noidungs_list),
        'selected_khoi_id': int(selected_khoi_id) if selected_khoi_id and str(selected_khoi_id).isdigit() else None,
        'selected_mon_id': int(selected_mon_id) if selected_mon_id and str(selected_mon_id).isdigit() else None,
        'selected_mach_id': int(selected_mach_id) if selected_mach_id and str(selected_mach_id).isdigit() else None,
    }

    if request.method == 'POST' and request.FILES.get('word_file'):
        if not selected_khoi_id or not selected_mon_id:
            messages.error(request, 'Vui lòng chọn Khối và Môn học trước khi tải lên đề thi.')
            return render(request, 'question_bank/import_word.html', context_base)

        khoi_obj = Khoi.objects.filter(id=selected_khoi_id).first()
        mon_obj = MonHoc.objects.filter(id=selected_mon_id).first()
        if not khoi_obj or not mon_obj:
            messages.error(request, 'Khối hoặc Môn học không tồn tại.')
            return render(request, 'question_bank/import_word.html', context_base)

        khoi_name = khoi_obj.TenKhoi
        mon_name = mon_obj.TenMon

        target_machs_qs = MachKienThuc.objects.filter(Khoi_id=selected_khoi_id, MonHoc_id=selected_mon_id)
        if not target_machs_qs.exists():
            target_machs_qs = MachKienThuc.objects.filter(MonHoc_id=selected_mon_id)

        target_machs_list = list(target_machs_qs.values('id', 'TenMach'))
        target_noidungs_qs = NoiDungKienThuc.objects.filter(MachKienThuc__in=target_machs_qs)
        target_noidungs_list = list(target_noidungs_qs.values('id', 'TenNoidung', 'MachKienThuc_id'))

        selected_mach_obj = target_machs_qs.filter(id=selected_mach_id).first() if selected_mach_id else None

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
            
            api_key = getattr(settings, 'GROQ_API_KEY', '')
            if not api_key:
                messages.error(request, 'Cần cấu hình GROQ_API_KEY trong settings để sử dụng tính năng trích xuất thông minh.')
                return render(request, 'question_bank/import_word.html', context_base)
                
            groq_client = Groq(api_key=api_key)
            
            prompt = f"""
Bạn là một chuyên gia giáo dục tiểu học và hệ thống trích xuất, phân loại đề thi thông minh.
Thông tin cấu hình đề thi:
- Khối lớp: {khoi_name} (ID: {selected_khoi_id})
- Môn học: {mon_name} (ID: {selected_mon_id})
{f"- Mạch kiến thức được chỉ định sẵn: {selected_mach_obj.TenMach} (ID: {selected_mach_obj.id})" if selected_mach_obj else "- Mạch kiến thức: Hãy TỰ ĐỘNG PHÂN LOẠI từng câu hỏi vào Mạch kiến thức phù hợp nhất trong danh sách bên dưới."}

DANH SÁCH MẠCH KIẾN THỨC CỦA {mon_name.upper()} - {khoi_name.upper()}:
{json.dumps(target_machs_list, ensure_ascii=False, indent=2)}

DANH SÁCH NỘI DUNG KIẾN THỨC TƯƠNG ỨNG (NẾU CÓ):
{json.dumps(target_noidungs_list, ensure_ascii=False, indent=2)}

Dưới đây là toàn bộ nội dung HTML của đề thi:
--- BẮT ĐẦU ĐỀ THI ---
{raw_text}
--- KẾT THÚC ĐỀ THI ---

Nhiệm vụ 1: Bóc tách cấu trúc đề thi, câu hỏi, các phương án đáp án, đáp án đúng và xác định chính xác DẠNG CÂU HỎI.
Các dạng câu hỏi được hỗ trợ (chọn 1 cho trường "question_type"):
- "MCQ": Trắc nghiệm 1 lựa chọn đúng.
- "MSQ": Trắc nghiệm nhiều lựa chọn đúng.
- "TF": Trắc nghiệm Đúng/Sai (Gồm nhiều mệnh đề, yêu cầu đánh giá từng mệnh đề là Đúng hay Sai).
- "Matching": Câu hỏi ghép nối (Nối các mục ở 2 cột với nhau).
- "FIB": Câu hỏi điền khuyết (Điền từ vào chỗ trống).
- "Order": Sắp xếp thứ tự (Sắp xếp danh sách các mục theo thứ tự đúng).
- "EssayShort": Tự luận ngắn (Ví dụ: đặt câu, viết 1 đoạn văn ngắn, tính toán tự luận).
- "EssayLong": Tự luận dài (Ví dụ: Tập làm văn, viết bài văn).
Nếu là dạng tự luận, phần giải thích/đáp án/barem điểm phải được gán vào trường "explanation".

LƯU Ý CỰC KỲ QUAN TRỌNG VỀ ĐỊNH DẠNG:
1. BẠN PHẢI LOẠI BỎ CÁC THẺ HTML TRANG TRÍ (như <br>, <strong>, <p>, <span>...) ra khỏi nội dung câu hỏi và đáp án, CHỈ GIỮ LẠI PLAIN TEXT. 
   TUY NHIÊN, nếu câu hỏi hoặc đáp án có chứa hình ảnh (các tag <img src="IMAGE_X"> hoặc <img id="IMAGE_X">), bạn BẮT BUỘC phải giữ nguyên thẻ `<img src="IMAGE_X">` ở vị trí tương ứng trong văn bản `content` của câu hỏi hoặc `text` / `statement` / `left` / `right` của đáp án để không làm mất vị trí ảnh.
2. NẾU CÂU HỎI CÓ CÁC LỰA CHỌN ĐÁP ÁN (ví dụ A, B, C, D), BẠN BẮT BUỘC PHẢI TÁCH CHÚNG RA KHỎI NỘI DUNG CÂU HỎI VÀ ĐƯA VÀO MẢNG `answers`. KHÔNG ĐƯỢC GỘP LỰA CHỌN ĐÁP ÁN VÀO TRONG TRƯỜNG `content` CỦA CÂU HỎI.
3. PHẢI PHÂN LOẠI ĐÚNG DẠNG CÂU HỎI. Nếu câu hỏi có 4 phương án A,B,C,D thì đó là MCQ, không phải tự luận!

LƯU Ý VỀ HÌNH ẢNH: Trong văn bản HTML có các thẻ `<img src="IMAGE_X" id="IMAGE_X">`. 
- Nếu câu hỏi có chứa hình ảnh, hãy đặt giá trị `IMAGE_X` vào trường `image` của câu hỏi. Nếu không có, để null.
- Nếu đáp án/phương án có hình ảnh, hãy đặt giá trị `IMAGE_X` vào trường `image` (hoặc `left_image`, `right_image` tùy dạng) của phương án đó. Nếu không, để null.

Nhiệm vụ 2: TỰ ĐỘNG PHÂN LOẠI MẠCH KIẾN THỨC VÀ NỘI DUNG KIẾN THỨC:
- Với mỗi câu hỏi, bạn PHẢI phân tích nội dung câu hỏi và TỰ ĐỘNG PHÂN LOẠI vào một trong các Mạch kiến thức trong danh sách trên:
  + Gán "mach_id": ID của Mạch kiến thức phù hợp trong danh sách.
  + Gán "mach_name": Tên của Mạch kiến thức tương ứng.
- Nếu câu hỏi phù hợp với một Nội dung kiến thức cụ thể trong danh sách, hãy gán "noidung_id" là ID tương ứng và "noidung_name". Nếu không tìm thấy nội dung phù hợp, để null.
- Mọi câu hỏi đều có: "khoi_id": {selected_khoi_id}, "khoi_name": "{khoi_name}", "mon_id": {selected_mon_id}, "mon_name": "{mon_name}".
- Ước lượng mức độ nhận thức / độ khó ("muc_do"): "Mức 1" (Nhận biết), "Mức 2" (Thông hiểu), hoặc "Mức 3" (Vận dụng).

Nhiệm vụ 3: Kiểm duyệt và Giải đề tự động
- Kiểm duyệt: Phân tích nội dung đề thi. Nếu phát hiện kiến thức VƯỢT QUÁ chương trình Tiểu học {khoi_name} môn {mon_name}, hãy gán "is_out_of_scope": true và ghi rõ cảnh báo vào "scope_warning". Nếu bình thường, để false và null.
- Giải đề: Đóng vai trò là Giáo viên, nếu đề thi KHÔNG CÓ SẴN ĐÁP ÁN ở cuối hoặc không ghi rõ đáp án đúng, bạn phải TỰ ĐỘNG GIẢI các câu hỏi và điền đáp án đúng vào cấu trúc. ĐỒNG THỜI, gán cờ "is_ai_solved": true cho các câu hỏi mà bạn phải tự giải. Nếu đề đã có sẵn đáp án, gán false.

Yêu cầu bắt buộc: Trả về kết quả dưới định dạng OBJECT JSON gồm các trường:
- "is_out_of_scope": boolean
- "scope_warning": string hoặc null
- "groups": Mảng chứa các nhóm câu hỏi. (Nếu câu hỏi không thuộc đoạn văn/ngữ cảnh nào, hãy để group_content = null).

Cấu trúc mảng `answers` sẽ khác nhau tùy thuộc vào `question_type`:
- MCQ/MSQ: `answers`: [{{"text": "A. ...", "image": "IMAGE_X"}}], `correct`: 0 (với MCQ) hoặc [0, 2] (với MSQ).
- TF: `answers`: [{{"statement": "Mệnh đề 1", "image": "IMAGE_X", "correct_label": "Đúng"}}]. (correct_label chỉ nhận giá trị "Đúng" hoặc "Sai").
- Matching: `answers`: [{{"left": "Từ 1", "left_image": "IMAGE_X", "right": "Nghĩa 1", "right_image": "IMAGE_Y"}}].
- FIB: `answers`: ["Đáp án 1", "Đáp án 2"].
- Order: `answers`: ["Mục 1", "Mục 2", "Mục 3"].
- EssayShort/EssayLong: `answers`: [].

Ví dụ định dạng trả về:
{{
  "is_out_of_scope": false,
  "scope_warning": null,
  "groups": [
    {{
      "group_content": null,
      "questions": [
        {{
          "question_type": "MCQ",
          "content": "Câu 1: Số liền sau của số 39 là số nào? <img src=\"IMAGE_1\">",
          "image": "IMAGE_1",
          "answers": [{{"text": "A. 38", "image": null}}, {{"text": "B. 40", "image": null}}, {{"text": "C. 41", "image": null}}],
          "correct": 1,
          "explanation": "Số liền sau của 39 là 39 + 1 = 40.",
          "is_ai_solved": true,
          "muc_do": "Mức 1",
          "khoi_id": {selected_khoi_id}, "mon_id": {selected_mon_id}, "mach_id": {target_machs_list[0]['id'] if target_machs_list else 'null'}, "noidung_id": null,
          "khoi_name": "{khoi_name}", "mon_name": "{mon_name}", "mach_name": "{target_machs_list[0]['TenMach'] if target_machs_list else ''}", "noidung_name": ""
        }}
      ]
    }}
  ]
}}
Chỉ trả về chuỗi JSON (bắt đầu bằng {{ và kết thúc bằng }}), không kèm giải thích.
"""
            
            # Xây dựng nội dung message cho Groq
            user_content = [{'type': 'text', 'text': prompt}]
            
            # Đính kèm ảnh qua base64 cho Groq vision
            has_images = False
            for img_id, b64_str in images_dict.items():
                if b64_str.startswith('data:image/'):
                    try:
                        media_type = b64_str.split(';')[0].split(':')[1]  # e.g. image/png
                        b64_data = b64_str.split(';base64,')[1]
                        user_content.append({
                            'type': 'text',
                            'text': f'--- ĐÂY LÀ BỨC ẢNH {img_id} ---'
                        })
                        user_content.append({
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:{media_type};base64,{b64_data}'
                            }
                        })
                        has_images = True
                    except Exception:
                        pass
            
            model_name = getattr(settings, 'GROQ_MODEL', 'openai/gpt-oss-120b')
            groq_response = call_groq_chat(groq_client,
                model=model_name,
                messages=[{'role': 'user', 'content': user_content if has_images else prompt}],
                temperature=0.3,
                max_tokens=8192,
            )
            res_text = groq_response.choices[0].message.content.strip()
            if res_text.startswith('```json'):
                res_text = res_text[7:-3]
            elif res_text.startswith('```'):
                res_text = res_text[3:-3]
                
            parsed_data = extract_json_from_ai(res_text)
            
            # Chuẩn hóa dữ liệu phân loại & kiểm tra trùng lặp
            if isinstance(parsed_data, dict) and 'groups' in parsed_data:
                target_mach_map = {m['id']: m['TenMach'] for m in target_machs_list}
                target_nd_map = {n['id']: n['TenNoidung'] for n in target_noidungs_list}

                for group in parsed_data['groups']:
                    for q in group.get('questions', []):
                        q['khoi_id'] = int(selected_khoi_id)
                        q['khoi_name'] = khoi_name
                        q['mon_id'] = int(selected_mon_id)
                        q['mon_name'] = mon_name

                        if selected_mach_obj:
                            q['mach_id'] = selected_mach_obj.id
                            q['mach_name'] = selected_mach_obj.TenMach
                        elif q.get('mach_id') not in target_mach_map:
                            matched_id = None
                            for mid, mname in target_mach_map.items():
                                if mname.lower() in str(q.get('mach_name', '')).lower() or str(q.get('mach_name', '')).lower() in mname.lower():
                                    matched_id = mid
                                    break
                            if matched_id:
                                q['mach_id'] = matched_id
                                q['mach_name'] = target_mach_map[matched_id]
                            elif target_machs_list:
                                q['mach_id'] = target_machs_list[0]['id']
                                q['mach_name'] = target_machs_list[0]['TenMach']
                            else:
                                q['mach_id'] = None
                        else:
                            q['mach_name'] = target_mach_map.get(q.get('mach_id'), '')

                        if q.get('noidung_id') not in target_nd_map:
                            q['noidung_id'] = None
                        else:
                            q['noidung_name'] = target_nd_map.get(q.get('noidung_id'), '')

                        q['is_duplicate'] = CauHoi.objects.filter(
                            Khoi_id=q['khoi_id'],
                            MonHoc_id=q['mon_id'],
                            NoiDungCauHoi__iexact=q.get('content', '').strip()
                        ).exists()
            
            # Thay thế mã ảnh thành chuỗi Base64 thực tế để hiển thị
            def replace_image_codes(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if isinstance(v, str):
                            if v in images_dict:
                                obj[k] = images_dict[v]
                            else:
                                new_v = v
                                for img_id, img_base64 in images_dict.items():
                                    if img_id in new_v:
                                        new_v = new_v.replace(img_id, img_base64)
                                obj[k] = new_v
                        else:
                            replace_image_codes(v)
                elif isinstance(obj, list):
                    for item in obj:
                        replace_image_codes(item)
            
            replace_image_codes(parsed_data)
            
            context_result = dict(context_base)
            context_result['parsed_groups'] = json.dumps(parsed_data)
            return render(request, 'question_bank/import_word.html', context_result)
            
        except Exception as e:
            messages.error(request, f'Lỗi đọc file hoặc AI: {str(e)}')
            
    return render(request, 'question_bank/import_word.html', context_base)


@csrf_exempt
@login_required
@khao_thi_required
def api_suggest_question(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            khoi    = data.get('khoi', '').strip()
            mon     = data.get('mon', '').strip()
            mach    = data.get('mach', '').strip()
            noidung = data.get('noidung', '').strip()
            dang    = data.get('dang', '').strip()
            muc_do  = data.get('muc_do', '').strip()
            requirement = data.get('requirement', '').strip()
            group_content = data.get('group_content', '').strip()

            api_key = getattr(settings, 'GROQ_API_KEY', '')
            if not api_key:
                return JsonResponse({'error': 'Chưa cấu hình API Key cho Groq AI.'}, status=400)

            groq_client = Groq(api_key=api_key)

            # Xây dựng ngữ cảnh phân loại
            context_parts = []
            if khoi:    context_parts.append(f"Khối: {khoi}")
            if mon:     context_parts.append(f"Môn: {mon}")
            if mach:    context_parts.append(f"Mạch kiến thức: {mach}")
            if noidung: context_parts.append(f"Nội dung kiến thức: {noidung}")
            if dang:    context_parts.append(f"Dạng câu hỏi: {dang}")
            if muc_do:  context_parts.append(f"Mức độ: {muc_do}")
            context_str = '\n'.join(context_parts) if context_parts else 'Chưa chọn phân loại cụ thể'

            extra = f'\nYêu cầu thêm: {requirement}' if requirement else ''
            
            group_context = f'\nNGỮ LIỆU CHUNG (Dùng ngữ liệu này để đặt câu hỏi đọc hiểu / tính toán):\n"""\n{group_content}\n"""\n(BẮT BUỘC: Đặt câu hỏi dựa trên hoặc liên quan đến nội dung ngữ liệu này)' if group_content else ''

            if dang == 'Matching':
                prompt = f"""
Bạn là giáo viên Tiểu học Việt Nam. Hãy tạo 1 câu hỏi ghép nối (Matching) hoàn chỉnh theo yêu cầu:
{context_str}{extra}{group_context}

QUY TẮC BẮT BUỘC:
- Sinh câu lệnh đề bài (ví dụ: "Nối mỗi từ ở cột bên trái với ý nghĩa tương ứng ở cột bên phải:")
- Sinh đồng thời 3 đến 4 cặp ghép nối logic và chính xác. Cột trái và cột phải tương ứng với nhau.
- Trả về DUY NHẤT một chuỗi JSON hợp lệ theo định dạng sau (không markdown, không giải thích):
{{
    "question_content": "Yêu cầu đề bài...",
    "matching_pairs": [
        {{"left": "Từ hoặc vế trái 1", "right": "Nghĩa hoặc vế phải 1"}},
        {{"left": "Từ hoặc vế trái 2", "right": "Nghĩa hoặc vế phải 2"}},
        {{"left": "Từ hoặc vế trái 3", "right": "Nghĩa hoặc vế phải 3"}}
    ]
}}
"""
            elif dang == 'FIB':
                prompt = f"""
Bạn là giáo viên Tiểu học Việt Nam. Hãy tạo 1 câu hỏi điền khuyết (Fill in the Blank) hoàn chỉnh theo yêu cầu:
{context_str}{extra}{group_context}

QUY TẮC BẮT BUỘC:
- Sinh câu hoặc đoạn văn có chứa 2 đến 3 vị trí khuyết được đánh dấu bằng ký hiệu [...]
- Sinh đồng thời đáp án chính xác cho từng vị trí khuyết [...] theo đúng thứ tự xuất hiện.
- Trả về DUY NHẤT một chuỗi JSON hợp lệ theo định dạng sau (không markdown, không giải thích):
{{
    "question_content": "Điền từ thích hợp vào chỗ trống: Đoạn văn chứa [...] và [...] ở vị trí khuyết.",
    "fib_answers": ["đáp án cho chỗ trống 1", "đáp án cho chỗ trống 2"]
}}
"""
            elif dang == 'TF':
                prompt = f"""
Bạn là giáo viên Tiểu học Việt Nam. Hãy tạo 1 câu hỏi Đúng/Sai (Yes/No) hoàn chỉnh theo yêu cầu:
{context_str}{extra}{group_context}

QUY TẮC BẮT BUỘC:
- Nếu có ngữ liệu chung: sinh câu dẫn yêu cầu đánh giá nhận định theo đoạn văn.
- Nếu không có ngữ liệu: sinh nội dung mệnh đề/câu hỏi làm cơ sở.
- Sinh đồng thời 4 nhận định và xác định đáp án "Đúng" hoặc "Sai" cho từng nhận định.
- Trả về DUY NHẤT một chuỗi JSON hợp lệ theo định dạng sau (không markdown, không giải thích):
{{
    "question_content": "Câu hỏi / câu dẫn ở đây",
    "tf_statements": [
        {{"statement": "Nhận định 1...", "correct": "Đúng"}},
        {{"statement": "Nhận định 2...", "correct": "Sai"}},
        {{"statement": "Nhận định 3...", "correct": "Đúng"}},
        {{"statement": "Nhận định 4...", "correct": "Sai"}}
    ]
}}
"""
            else:
                prompt = f"""
Bạn là giáo viên Tiểu học Việt Nam. Hãy tạo 1 câu hỏi thi theo yêu cầu sau:

{context_str}{extra}{group_context}

QUY TẮC BẮT BUỘC:
- Chỉ viết PHẦN ĐỀ BÀI của câu hỏi (câu hỏi đặt ra cho học sinh).
- TUYỆT ĐỐI KHÔNG được viết các phương án trả lời (A., B., C., D., 1., 2., ...) vào trong câu hỏi.
- TUYỆT ĐỐI KHÔNG viết đáp án, gợi ý, hoặc giải thích.
- Không có tiền tố "Câu 1:" hay số thứ tự.
- Câu hỏi ngắn gọn, rõ ràng, phù hợp học sinh Tiểu học.
- Trả về JSON: {{"question_content": "Câu hỏi ở đây"}}
"""
            groq_response = call_groq_chat(groq_client,
                model=getattr(settings, 'GROQ_MODEL', 'openai/gpt-oss-120b'),
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.5,
                max_tokens=2048,
            )
            res_text = groq_response.choices[0].message.content.strip()
            if res_text.startswith('```json'): res_text = res_text[7:]
            if res_text.startswith('```'):     res_text = res_text[3:]
            if res_text.endswith('```'):       res_text = res_text[:-3]

            result = extract_json_from_ai(res_text)
            q_content = result.get('question_content', '')

            # Hậu xử lý: cắt bỏ các dòng đáp án nếu AI vẫn thêm vào
            import re
            lines = q_content.splitlines()
            clean_lines = [
                line for line in lines
                if not re.match(r'^\s*[A-Da-d][.)]\s+', line)   # Loại "A. ...", "B) ..."
                and not re.match(r'^\s*[1-4][.)]\s+', line)      # Loại "1. ...", "2) ..."
            ]
            q_content = '\n'.join(clean_lines).strip()

            return JsonResponse({
                'success': True,
                'question_content': q_content,
                'matching_pairs': result.get('matching_pairs', []),
                'fib_answers': result.get('fib_answers', []),
                'tf_statements': result.get('tf_statements', [])
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=400)


@csrf_exempt
@login_required
@khao_thi_required
def api_suggest_group_content(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            khoi    = data.get('khoi', '').strip()
            mon     = data.get('mon', '').strip()
            mach    = data.get('mach', '').strip()
            noidung = data.get('noidung', '').strip()
            requirement = data.get('requirement', '').strip()

            api_key = getattr(settings, 'GROQ_API_KEY', '')
            if not api_key:
                return JsonResponse({'error': 'Chưa cấu hình API Key cho Groq AI.'}, status=400)

            groq_client = Groq(api_key=api_key)

            # Xây dựng ngữ cảnh phân loại
            context_parts = []
            if khoi:    context_parts.append(f"Khối: {khoi}")
            if mon:     context_parts.append(f"Môn: {mon}")
            if mach:    context_parts.append(f"Mạch kiến thức: {mach}")
            if noidung: context_parts.append(f"Nội dung kiến thức: {noidung}")
            context_str = '\n'.join(context_parts) if context_parts else 'Chưa chọn phân loại cụ thể'

            extra = f'\nYêu cầu thêm: {requirement}' if requirement else ''

            prompt = f"""
Bạn là giáo viên Tiểu học Việt Nam. Hãy tạo phần Nội dung chung (ngữ liệu chung như đoạn văn, bài thơ, tình huống) để dùng chung cho 1 nhóm câu hỏi, theo yêu cầu sau:

{context_str}{extra}

QUY TẮC BẮT BUỘC:
- Chỉ viết phần ngữ liệu, văn bản, đoạn văn, hoặc bài thơ.
- Độ dài và nội dung phù hợp với học sinh Tiểu học.
- TUYỆT ĐỐI KHÔNG viết các câu hỏi con đi kèm (1, 2, 3...).
- Trả về JSON theo định dạng sau:
{{
  "group_name": "Tên ngắn gọn cho nhóm ngữ liệu này (Ví dụ: Chiếc lá cuối cùng, Đoạn văn bảo vệ môi trường)",
  "group_content": "Ngữ liệu ở đây"
}}
"""
            groq_response = call_groq_chat(groq_client,
                model=getattr(settings, 'GROQ_MODEL', 'openai/gpt-oss-120b'),
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.7,
                max_tokens=2048,
            )
            res_text = groq_response.choices[0].message.content.strip()
            if res_text.startswith('```json'): res_text = res_text[7:]
            if res_text.startswith('```'):     res_text = res_text[3:]
            if res_text.endswith('```'):       res_text = res_text[:-3]

            result = extract_json_from_ai(res_text)
            g_content = result.get('group_content', '')
            g_name = result.get('group_name', '')

            return JsonResponse({'success': True, 'group_content': g_content.strip(), 'group_name': g_name.strip()})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=400)


@csrf_exempt
@login_required
@khao_thi_required
def api_generate_ai_variations(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            original_q = data.get('question_content', '')
            requirement = data.get('requirement', '').strip()
            dang = data.get('dang', 'MCQ').strip()
            
            if not original_q.strip():
                return JsonResponse({'error': 'Vui lòng nhập nội dung câu hỏi.'}, status=400)
            
            api_key = getattr(settings, 'GROQ_API_KEY', '')
            if not api_key:
                return JsonResponse({'error': 'Chưa cấu hình API Key cho Groq AI.'}, status=400)
                
            groq_client = Groq(api_key=api_key)
            
            # Xây dựng yêu cầu bổ sung từ người dùng
            extra_instruction = ''
            if requirement:
                extra_instruction = f'\nYêu cầu đặc biệt từ giáo viên: {requirement}'
            
            is_essay = dang.startswith('Essay') or dang == 'Tự luận' or dang == 'TL'
            
            if is_essay:
                prompt = f"""
Bạn là giáo viên Tiểu học Việt Nam. Nhiệm vụ: tạo đáp án mẫu, hướng dẫn giải hoặc barem chấm điểm chi tiết cho câu hỏi tự luận bên dưới.

Câu hỏi: {original_q}{extra_instruction}

Yêu cầu:
- Viết đáp án mẫu rõ ràng, phù hợp với trình độ học sinh Tiểu học.
- Trả về JSON theo định dạng sau (không kèm markdown, không giải thích thêm):
{{
    "essay_answer": "Nội dung đáp án mẫu hoặc hướng dẫn chấm..."
}}
"""
            elif dang == 'Matching':
                prompt = f"""
Bạn là giáo viên Tiểu học Việt Nam. Nhiệm vụ: tạo 3 đến 4 cặp ghép nối phù hợp, có quan hệ logic và chính xác cho câu hỏi ghép nối dưới đây.
Câu hỏi: {original_q}{extra_instruction}

Yêu cầu:
- Sinh các cặp ghép có vế trái và vế phải tương ứng.
- Trả về JSON theo định dạng sau (không kèm markdown, không giải thích thêm):
{{
    "matching_pairs": [
        {{"left": "Từ/vế trái 1", "right": "Nghĩa/vế phải 1"}},
        {{"left": "Từ/vế trái 2", "right": "Nghĩa/vế phải 2"}},
        {{"left": "Từ/vế trái 3", "right": "Nghĩa/vế phải 3"}}
    ]
}}
"""
            elif dang == 'FIB':
                prompt = f"""
Bạn là giáo viên Tiểu học Việt Nam. Nhiệm vụ: xác định các vị trí khuyết [...] trong câu hỏi dưới đây và tạo đáp án chính xác cho từng vị trí khuyết theo thứ tự xuất hiện.
Câu hỏi: {original_q}{extra_instruction}

Yêu cầu:
- Nếu câu hỏi chưa có vị trí khuyết rõ ràng, hãy xác định các từ khóa trọng tâm phù hợp để làm đáp án điền khuyết.
- Trả về JSON theo định dạng sau (không kèm markdown, không giải thích thêm):
{{
    "fib_answers": ["đáp án cho vị trí 1", "đáp án cho vị trí 2"]
}}
"""
            elif dang == 'TF':
                prompt = f"""
Bạn là giáo viên Tiểu học Việt Nam. Nhiệm vụ: tạo 4 nhận định liên quan đến câu hỏi dưới đây và xác định giá trị Đúng hoặc Sai cho từng nhận định.
Câu hỏi: {original_q}{extra_instruction}

Yêu cầu:
- Tạo 4 nhận định rõ ràng, phù hợp học sinh Tiểu học.
- Xác định chính xác "Đúng" hoặc "Sai" cho từng nhận định.
- Trả về JSON theo định dạng sau (không kèm markdown, không giải thích thêm):
{{
    "tf_statements": [
        {{"statement": "Nhận định 1...", "correct": "Đúng"}},
        {{"statement": "Nhận định 2...", "correct": "Sai"}},
        {{"statement": "Nhận định 3...", "correct": "Đúng"}},
        {{"statement": "Nhận định 4...", "correct": "Sai"}}
    ]
}}
"""
            else:
                prompt = f"""
Bạn là giáo viên Tiểu học Việt Nam. Nhiệm vụ: tạo các phương án trả lời cho câu hỏi trắc nghiệm bên dưới và chỉ rõ đáp án đúng.

Câu hỏi: {original_q}{extra_instruction}

Yêu cầu:
- Mặc định tạo 4 phương án (A, B, C, D), trừ khi yêu cầu đặc biệt chỉ định số lượng khác.
- Chỉ có 1 đáp án đúng.
- Các đáp án sai phải hợp lý, không quá dễ đoán.
- Nếu câu hỏi có công thức toán, hãy dùng ký hiệu LaTeX (VD: \\frac{{1}}{{2}} cho phân số 1/2).
- Trả về JSON theo định dạng sau (không kèm markdown, không giải thích thêm):
{{
    "answers": ["Nội dung A", "Nội dung B", "Nội dung C", "Nội dung D"],
    "correct": 0
}}
(correct là chỉ số 0-based của đáp án đúng)
"""
            groq_response = call_groq_chat(groq_client,
                model=getattr(settings, 'GROQ_MODEL', 'openai/gpt-oss-120b'),
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.5,
                max_tokens=2048,
            )
            res_text = groq_response.choices[0].message.content.strip()
            if res_text.startswith('```json'):
                res_text = res_text[7:]
            if res_text.startswith('```'):
                res_text = res_text[3:]
            if res_text.endswith('```'):
                res_text = res_text[:-3]
                
            result = extract_json_from_ai(res_text)
            
            if is_essay:
                return JsonResponse({'success': True, 'question': {
                    'essay_answer': result.get('essay_answer', '')
                }})
            elif dang == 'Matching':
                return JsonResponse({'success': True, 'question': {
                    'matching_pairs': result.get('matching_pairs', [])
                }})
            elif dang == 'FIB':
                return JsonResponse({'success': True, 'question': {
                    'fib_answers': result.get('fib_answers', [])
                }})
            elif dang == 'TF':
                return JsonResponse({'success': True, 'question': {
                    'tf_statements': result.get('tf_statements', [])
                }})
            else:
                return JsonResponse({'success': True, 'question': {
                    'answers': result.get('answers', []),
                    'correct': result.get('correct', 0)
                }})
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

            def safe_int_id(val):
                try:
                    return int(val) if val not in [None, '', 'null'] else None
                except (ValueError, TypeError):
                    return None
            
            def process_and_save_inline_images(html_text):
                if not html_text:
                    return html_text
                soup = BeautifulSoup(html_text, 'html.parser')
                has_changes = False
                for img in soup.find_all('img'):
                    src = img.get('src')
                    if src and src.startswith('data:image/'):
                        try:
                            fmt, imgstr = src.split(';base64,')
                            ext = fmt.split('/')[-1]
                            # Decode and save
                            img_bytes = base64.b64decode(imgstr)
                            file_name = f"{uuid.uuid4()}.{ext}"
                            from django.core.files.storage import default_storage
                            saved_path = default_storage.save(f"questions/{file_name}", ContentFile(img_bytes))
                            img['src'] = settings.MEDIA_URL + saved_path
                            has_changes = True
                        except Exception:
                            pass
                return str(soup) if has_changes else html_text

            with transaction.atomic():
                for group in groups:
                    group_content = group.get('group_content')
                    nhom_obj = None
                    
                    if group_content and group_content.strip():
                        # Lấy tạm khối môn từ câu hỏi đầu tiên của nhóm nếu có
                        first_q = group.get('questions', [{}])[0]
                        g_khoi_id = safe_int_id(first_q.get('khoi_id'))
                        g_mon_id = safe_int_id(first_q.get('mon_id'))
                        g_mach_id = safe_int_id(first_q.get('mach_id'))
                        g_noidung_id = safe_int_id(first_q.get('noidung_id'))
                        
                        nhom_obj = NhomCauHoi.objects.create(
                            Khoi_id=g_khoi_id,
                            MonHoc_id=g_mon_id,
                            MachKienThuc_id=g_mach_id,
                            NoiDungKienThuc_id=g_noidung_id,
                            TenNhom="Nhóm trích xuất từ Word",
                            NoiDungChung=group_content.strip(),
                            NguoiTao=getattr(request.user, 'giaovien', None)
                        )
                        
                    for q_data in group.get('questions', []):
                        q_type = q_data.get('question_type', 'MCQ')
                        is_trac_nghiem = q_type in ['MCQ', 'MSQ', 'TF', 'Matching', 'FIB', 'Order']
                        
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
                        # Lưu các ảnh inline trong câu hỏi
                        content = process_and_save_inline_images(content)
                        
                        khoi_id = q_data.get('khoi_id')
                        mon_id = q_data.get('mon_id')
                        muc_do = q_data.get('muc_do', 'Mức 1')
                        if muc_do not in ['Mức 1', 'Mức 2', 'Mức 3']:
                            muc_do = 'Mức 1'

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
                            Khoi_id=safe_int_id(khoi_id),
                            MonHoc_id=safe_int_id(mon_id),
                            MachKienThuc_id=safe_int_id(q_data.get('mach_id')),
                            NoiDungKienThuc_id=safe_int_id(q_data.get('noidung_id')),
                            NhomCauHoi=nhom_obj,
                            HinhThuc='Trắc nghiệm' if is_trac_nghiem else 'Tự luận',
                            DangCauHoi=q_type,
                            MucDo=muc_do, 
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
                                ans_text = ans_obj.get('text', '') if isinstance(ans_obj, dict) else ans_obj
                                ans_text = process_and_save_inline_images(ans_text)
                                ans_img = get_image_file(ans_obj.get('image')) if isinstance(ans_obj, dict) else None
                                if ans_text.startswith(f"{label}.") or ans_text.startswith(f"{label})"):
                                    ans_text = ans_text[2:].strip()
                                DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDungTrai=label, NoiDung=ans_text, HinhAnh=ans_img, LaDapAnDung=(i == correct_idx))
                                
                        elif q_type == 'MSQ':
                            corrects = q_data.get('correct', [])
                            if not isinstance(corrects, list):
                                corrects = [corrects]
                            for i, ans_obj in enumerate(answers):
                                label = chr(65 + i)
                                ans_text = ans_obj.get('text', '') if isinstance(ans_obj, dict) else ans_obj
                                ans_text = process_and_save_inline_images(ans_text)
                                ans_img = get_image_file(ans_obj.get('image')) if isinstance(ans_obj, dict) else None
                                if ans_text.startswith(f"{label}.") or ans_text.startswith(f"{label})"):
                                    ans_text = ans_text[2:].strip()
                                DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDungTrai=label, NoiDung=ans_text, HinhAnh=ans_img, LaDapAnDung=(i in corrects))
                                
                        elif q_type == 'TF':
                            labels_set = set()
                            for i, ans_obj in enumerate(answers):
                                stmt = ans_obj.get('statement', '')
                                stmt = process_and_save_inline_images(stmt)
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
                                left_val = process_and_save_inline_images(left_val)
                                right_val = ans_obj.get('right', '')
                                right_val = process_and_save_inline_images(right_val)
                                left_img = get_image_file(ans_obj.get('left_image'))
                                right_img = get_image_file(ans_obj.get('right_image'))
                                DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDungTrai=left_val, NoiDung=right_val, HinhAnhTrai=left_img, HinhAnh=right_img, LaDapAnDung=True)
                                
                        elif q_type == 'FIB':
                            for i, ans_text in enumerate(answers):
                                ans_text = process_and_save_inline_images(ans_text)
                                DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDung=ans_text, LaDapAnDung=True)
                                
                        elif q_type == 'Order':
                            for i, ans_obj in enumerate(answers):
                                ans_text = ans_obj.get('text', '') if isinstance(ans_obj, dict) else ans_obj
                                ans_text = process_and_save_inline_images(ans_text)
                                ans_img = get_image_file(ans_obj.get('image')) if isinstance(ans_obj, dict) else None
                                DapAn.objects.create(CauHoi=q, ThuTu=i, NoiDung=ans_text, HinhAnh=ans_img, LaDapAnDung=True)
                                
                        count += 1
                        
            msg = f'Đã lưu thành công {count} câu hỏi!'
            if duplicate_count > 0:
                msg += f' Đã bỏ qua {duplicate_count} câu hỏi bị trùng lặp.'
            return JsonResponse({'success': True, 'message': msg})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=400)

@login_required
@khao_thi_required
def question_preview(request, pk):
    cau_hoi = get_object_or_404(CauHoi, pk=pk)
    return render(request, 'question_bank/preview.html', {'cau_hoi': cau_hoi})

