from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db.models import Q
from core.models import ThongBao
from core.notification_service import (
    get_user_notifications,
    mark_notification_as_read,
    mark_all_as_read,
    get_user_role,
    format_time_ago,
    sync_system_notifications,
)


@login_required
@require_GET
def api_get_notifications(request):
    """
    API trả về danh sách thông báo và số lượng chưa đọc dạng JSON.
    Hỗ trợ AJAX polling hoặc refresh dropdown thông báo.
    """
    data = get_user_notifications(request.user, limit=20)
    return JsonResponse({
        'success': True,
        'unread_count': data['unread_count'],
        'total_count': data['total_count'],
        'notifications': data['notifications'],
    })


@login_required
@require_POST
def api_mark_read(request, pk):
    """
    API đánh dấu 1 thông báo là đã đọc.
    """
    success = mark_notification_as_read(pk, request.user)
    data = get_user_notifications(request.user, limit=1)
    return JsonResponse({
        'success': success,
        'unread_count': data['unread_count']
    })


@login_required
@require_POST
def api_mark_all_read(request):
    """
    API đánh dấu tất cả thông báo của người dùng là đã đọc.
    """
    count = mark_all_as_read(request.user)
    return JsonResponse({
        'success': True,
        'updated_count': count,
        'unread_count': 0
    })


@login_required
def notification_list_view(request):
    """
    Trang danh sách đầy đủ tất cả các thông báo của người dùng (có phân trang và lọc).
    """
    try:
        sync_system_notifications()
    except Exception:
        pass

    user = request.user
    user_role = get_user_role(user)

    # Xây dựng query
    query = Q(NguoiNhan=user)
    role_queries = Q(NguoiNhan__isnull=True) & (Q(VaiTro='ALL') | Q(VaiTro__isnull=True) | Q(VaiTro=''))
    if user_role == 'ADMIN':
        role_queries |= Q(NguoiNhan__isnull=True, VaiTro__in=['ADMIN', 'BGH', 'TCM', 'GIAO_VIEN'])
    elif user_role == 'BGH':
        role_queries |= Q(NguoiNhan__isnull=True, VaiTro__in=['BGH', 'TCM'])
    elif user_role == 'TCM':
        role_queries |= Q(NguoiNhan__isnull=True, VaiTro__in=['TCM', 'GIAO_VIEN'])
    elif user_role == 'GIAO_VIEN':
        role_queries |= Q(NguoiNhan__isnull=True, VaiTro='GIAO_VIEN')

    query |= role_queries

    # Filter theo loại hoặc trạng thái nếu có
    filter_type = request.GET.get('loai', '').strip()
    status_filter = request.GET.get('trang_thai', '').strip()
    search_q = request.GET.get('q', '').strip()

    qs = ThongBao.objects.filter(query)

    if filter_type in ['info', 'warning', 'danger', 'success']:
        qs = qs.filter(Loai=filter_type)

    if search_q:
        qs = qs.filter(Q(TieuDe__icontains=search_q) | Q(NoiDung__icontains=search_q))

    qs = qs.prefetch_related('NguoiDaDoc').order_by('-NgayTao')

    read_ids = set(user.thong_bao_da_doc_set.values_list('id', flat=True))

    processed_list = []
    for tb in qs:
        if tb.NguoiNhan_id == user.id:
            is_read = tb.DaDoc
        else:
            is_read = tb.id in read_ids

        if status_filter == 'unread' and is_read:
            continue
        if status_filter == 'read' and not is_read:
            continue

        processed_list.append({
            'id': tb.id,
            'tieu_de': tb.TieuDe,
            'noi_dung': tb.NoiDung,
            'loai': tb.Loai,
            'icon': tb.Icon,
            'lien_ket': tb.LienKet or '#',
            'is_read': is_read,
            'time_ago': format_time_ago(tb.NgayTao),
            'ngay_tao': tb.NgayTao.strftime('%d/%m/%Y %H:%M'),
        })

    paginator = Paginator(processed_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    unread_total = get_user_notifications(user, limit=1)['unread_count']

    return render(request, 'core/notification_list.html', {
        'page_obj': page_obj,
        'filter_type': filter_type,
        'status_filter': status_filter,
        'search_q': search_q,
        'unread_total': unread_total,
        'total_items': len(processed_list),
    })

