import datetime
from django.utils import timezone
from django.db.models import Q
from core.models import ThongBao, GiaoVien
from matrix.models import MaTran, DeadlineGiaoVien
from exam.models import DeThi
from schedule.models import LichThi


def get_user_role(user):
    """
    Xác định vai trò của người dùng để phân phối thông báo:
    - ADMIN
    - BGH
    - TCM
    - GIAO_VIEN
    """
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'ADMIN'
    try:
        gv = user.giaovien
        if gv.ChucVu in ['Hiệu trưởng', 'Phó hiệu trưởng']:
            return 'BGH'
        elif gv.ChucVu in ['Tổ trưởng chuyên môn', 'Tổ phó chuyên môn']:
            return 'TCM'
        elif gv.ChucVu == 'Nhân viên văn thư':
            return 'ADMIN'
        else:
            return 'GIAO_VIEN'
    except Exception:
        return 'GIAO_VIEN'


def format_time_ago(dt):
    if not dt:
        return ""
    now = timezone.now()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 0:
        return "Vừa xong"
    if seconds < 60:
        return "Vừa xong"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} phút trước"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} giờ trước"
    days = hours // 24
    if days == 1:
        return f"Hôm qua lúc {dt.strftime('%H:%M')}"
    if days < 7:
        return f"{days} ngày trước"
    return dt.strftime("%d/%m/%Y %H:%M")


def create_notification(tieu_de, noi_dung, nguoi_nhan=None, vai_tro='ALL', loai='info', lien_ket=None, icon=None, ref_key=None):
    """
    Tạo hoặc cập nhật thông báo trong hệ thống.
    """
    if not icon:
        if loai == 'danger':
            icon = 'fas fa-exclamation-circle'
        elif loai == 'warning':
            icon = 'fas fa-exclamation-triangle'
        elif loai == 'success':
            icon = 'fas fa-check-circle'
        else:
            icon = 'fas fa-bell'

    if ref_key:
        tb, created = ThongBao.objects.get_or_create(
            RefKey=ref_key,
            defaults={
                'NguoiNhan': nguoi_nhan,
                'VaiTro': vai_tro,
                'TieuDe': tieu_de,
                'NoiDung': noi_dung,
                'Loai': loai,
                'Icon': icon,
                'LienKet': lien_ket or '',
            }
        )
        if not created:
            # Cập nhật thông tin nếu có thay đổi
            tb.TieuDe = tieu_de
            tb.NoiDung = noi_dung
            tb.Loai = loai
            tb.Icon = icon
            if lien_ket:
                tb.LienKet = lien_ket
            tb.save(update_fields=['TieuDe', 'NoiDung', 'Loai', 'Icon', 'LienKet'])
        return tb
    else:
        return ThongBao.objects.create(
            NguoiNhan=nguoi_nhan,
            VaiTro=vai_tro,
            TieuDe=tieu_de,
            NoiDung=noi_dung,
            Loai=loai,
            Icon=icon,
            LienKet=lien_ket or '',
        )


def sync_system_notifications():
    """
    Đồng bộ các thông báo hệ thống dựa trên dữ liệu thực tế (Ma trận, Đề thi, Lịch thi, Deadline).
    Chạy tự động để người dùng luôn nhận được thông báo mới nhất.
    """
    today = timezone.now().date()

    # 1. Ma trận đang chờ duyệt (Dành cho BGH & Admin)
    for m in MaTran.objects.filter(TrangThai='Chờ duyệt'):
        mon_str = m.MonHoc.TenMon if m.MonHoc else ""
        khoi_str = m.Khoi.TenKhoi if m.Khoi else ""
        create_notification(
            tieu_de=f"Ma trận chờ duyệt: {m.TenMaTran}",
            noi_dung=f"Ma trận môn {mon_str} ({khoi_str}) đang chờ Ban Giám Hiệu phê duyệt.",
            vai_tro='BGH',
            loai='warning',
            icon='fas fa-th-list',
            lien_ket=f"/ma-tran/{m.id}/",
            ref_key=f"matran_choduyet_{m.id}"
        )

    # 2. Deadline nộp/sửa đề của Ma trận
    for m in MaTran.objects.exclude(TrangThai__in=['Nháp', 'Đã hủy']):
        dl = m.deadline_hien_tai
        if not dl:
            continue
        days = (dl - today).days
        dl_str = dl.strftime('%d/%m/%Y')
        mon_str = m.MonHoc.TenMon if m.MonHoc else ""
        khoi_str = m.Khoi.TenKhoi if m.Khoi else ""

        if days < 0:
            create_notification(
                tieu_de=f"Quá hạn nộp đề: {m.TenMaTran}",
                noi_dung=f"Ma trận môn {mon_str} ({khoi_str}) đã quá hạn nộp đề {abs(days)} ngày (Hạn: {dl_str}).",
                vai_tro='TCM',
                loai='danger',
                icon='fas fa-clock',
                lien_ket=f"/ma-tran/{m.id}/",
                ref_key=f"matran_dl_overdue_{m.id}_{dl}"
            )
        elif days <= 2:
            day_text = "Hôm nay là hạn chót" if days == 0 else (f"Còn 1 ngày nữa" if days == 1 else f"Còn {days} ngày nữa")
            create_notification(
                tieu_de=f"Sắp đến hạn nộp đề: {m.TenMaTran}",
                noi_dung=f"{day_text} đến hạn nộp đề ma trận môn {mon_str} ({khoi_str}) (Hạn: {dl_str}).",
                vai_tro='TCM',
                loai='warning',
                icon='fas fa-hourglass-half',
                lien_ket=f"/ma-tran/{m.id}/",
                ref_key=f"matran_dl_near_{m.id}_{dl}_{days}"
            )

    # 3. Đề thi mới nộp chờ phê duyệt (Dành cho TCM & BGH)
    for d in DeThi.objects.filter(TrangThai='Đã nộp'):
        mon_str = d.MonHoc.TenMon if d.MonHoc else ""
        khoi_str = d.Khoi.TenKhoi if d.Khoi else ""
        create_notification(
            tieu_de=f"Đề thi mới nộp chờ duyệt: {d.TenDe}",
            noi_dung=f"Đề thi môn {mon_str} ({khoi_str}) đã được gửi lên và đang chờ phê duyệt.",
            vai_tro='TCM',
            loai='info',
            icon='fas fa-file-alt',
            lien_ket="/de-thi/",
            ref_key=f"dethi_danop_{d.id}"
        )

    # 4. Lịch thi sắp tới trong vòng 7 ngày
    for lt in LichThi.objects.all():
        delta = (lt.NgayThi - today).days
        if 0 <= delta <= 7:
            mon_str = lt.MonHoc.TenMon if lt.MonHoc else ""
            khoi_str = lt.Khoi.TenKhoi if lt.Khoi else ""
            ngay_str = lt.NgayThi.strftime('%d/%m/%Y')
            gio_str = f"{lt.GioBatDau.strftime('%H:%M')} - {lt.GioKetThuc.strftime('%H:%M')}"
            
            day_text = "Hôm nay" if delta == 0 else (f"Ngày mai" if delta == 1 else f"Còn {delta} ngày")
            create_notification(
                tieu_de=f"Lịch thi sắp tới: {mon_str} - {khoi_str} ({day_text})",
                noi_dung=f"Kỳ thi {lt.KyThi} ({lt.HocKy}) diễn ra vào {ngay_str} - {lt.CaThi} ({gio_str}).",
                vai_tro='ALL',
                loai='info',
                icon='fas fa-calendar-check',
                lien_ket="/lich-thi/",
                ref_key=f"lichthi_saptoi_{lt.id}_{lt.NgayThi}"
            )

    # 5. Phân công Deadline cá nhân cho từng Giáo viên
    for dlgv in DeadlineGiaoVien.objects.select_related('GiaoVien', 'MaTran'):
        if not dlgv.GiaoVien or not dlgv.GiaoVien.user:
            continue
        gv_user = dlgv.GiaoVien.user
        days = (dlgv.Deadline - today).days
        dl_str = dlgv.Deadline.strftime('%d/%m/%Y')
        mt_name = dlgv.MaTran.TenMaTran if dlgv.MaTran else "Ma trận"

        if days < 0:
            create_notification(
                tieu_de=f"Quá hạn làm đề thi: {mt_name}",
                noi_dung=f"Bạn đã quá hạn nộp đề cho ma trận '{mt_name}' {abs(days)} ngày (Hạn chót: {dl_str}).",
                nguoi_nhan=gv_user,
                vai_tro=None,
                loai='danger',
                icon='fas fa-calendar-times',
                lien_ket="/de-thi/",
                ref_key=f"dlgv_overdue_{dlgv.id}_{dlgv.Deadline}"
            )
        elif days <= 2:
            day_text = "Hôm nay là hạn chót" if days == 0 else (f"Bạn còn 1 ngày" if days == 1 else f"Bạn còn {days} ngày")
            create_notification(
                tieu_de=f"Sắp đến hạn nộp đề thi: {mt_name}",
                noi_dung=f"{day_text} để nộp đề cho ma trận '{mt_name}' (Hạn chót: {dl_str}).",
                nguoi_nhan=gv_user,
                vai_tro=None,
                loai='warning',
                icon='fas fa-stopwatch',
                lien_ket="/de-thi/",
                ref_key=f"dlgv_near_{dlgv.id}_{dlgv.Deadline}_{days}"
            )
        else:
            create_notification(
                tieu_de=f"Phân công làm đề thi: {mt_name}",
                noi_dung=f"Bạn được phân công làm đề cho ma trận '{mt_name}'. Hạn chót nộp: {dl_str}.",
                nguoi_nhan=gv_user,
                vai_tro=None,
                loai='info',
                icon='fas fa-tasks',
                lien_ket="/de-thi/",
                ref_key=f"dlgv_assigned_{dlgv.id}_{dlgv.Deadline}"
            )


def get_user_notifications(user, limit=20):
    """
    Lấy danh sách thông báo dành riêng cho người dùng hiện tại kèm số lượng chưa đọc.
    """
    if not user or not user.is_authenticated:
        return {'notifications': [], 'unread_count': 0, 'total_count': 0}

    # Đồng bộ thông báo mới nhất từ các sự kiện hệ thống
    try:
        sync_system_notifications()
    except Exception as e:
        # Nếu có lỗi khi sync (ví dụ thiếu bảng trong quá trình dev), không làm crash trang
        pass

    user_role = get_user_role(user)

    # Xây dựng query lọc thông báo
    # 1. Thông báo gửi trực tiếp cho user
    query = Q(NguoiNhan=user)

    # 2. Thông báo theo vai trò hoặc chung cho toàn trường
    role_queries = Q(NguoiNhan__isnull=True) & (Q(VaiTro='ALL') | Q(VaiTro__isnull=True) | Q(VaiTro=''))

    if user_role == 'ADMIN':
        # Admin thấy được thông báo của BGH, TCM và ALL
        role_queries |= Q(NguoiNhan__isnull=True, VaiTro__in=['ADMIN', 'BGH', 'TCM', 'GIAO_VIEN'])
    elif user_role == 'BGH':
        # BGH thấy thông báo BGH, ALL, và TCM
        role_queries |= Q(NguoiNhan__isnull=True, VaiTro__in=['BGH', 'TCM'])
    elif user_role == 'TCM':
        role_queries |= Q(NguoiNhan__isnull=True, VaiTro__in=['TCM', 'GIAO_VIEN'])
    elif user_role == 'GIAO_VIEN':
        role_queries |= Q(NguoiNhan__isnull=True, VaiTro='GIAO_VIEN')

    query |= role_queries

    all_qs = ThongBao.objects.filter(query).prefetch_related('NguoiDaDoc').order_by('-NgayTao')

    total_count = all_qs.count()

    # Xử lý danh sách và tính unread
    result_list = []
    unread_count = 0

    read_notif_ids = set(user.thong_bao_da_doc_set.values_list('id', flat=True))

    for tb in all_qs[:limit]:
        if tb.NguoiNhan_id == user.id:
            is_read = tb.DaDoc
        else:
            is_read = tb.id in read_notif_ids

        if not is_read:
            unread_count += 1

        result_list.append({
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

    # Nếu limit nhỏ hơn total, tính chính xác số unread cho toàn bộ
    if total_count > limit:
        # Đếm unread chính xác
        unread_direct = ThongBao.objects.filter(NguoiNhan=user, DaDoc=False).count()
        unread_broadcast = ThongBao.objects.filter(role_queries).exclude(NguoiDaDoc=user).count()
        unread_count = unread_direct + unread_broadcast

    return {
        'notifications': result_list,
        'unread_count': unread_count,
        'total_count': total_count
    }


def mark_notification_as_read(notification_id, user):
    """
    Đánh dấu 1 thông báo là đã đọc bởi user.
    """
    if not user or not user.is_authenticated:
        return False
    try:
        tb = ThongBao.objects.get(id=notification_id)
        tb.mark_as_read(user)
        return True
    except ThongBao.DoesNotExist:
        return False


def mark_all_as_read(user):
    """
    Đánh dấu tất cả thông báo thuộc về user là đã đọc.
    """
    if not user or not user.is_authenticated:
        return 0

    user_role = get_user_role(user)

    # 1. Các thông báo trực tiếp
    updated = ThongBao.objects.filter(NguoiNhan=user, DaDoc=False).update(DaDoc=True)

    # 2. Các thông báo broadcast
    role_queries = Q(NguoiNhan__isnull=True) & (Q(VaiTro='ALL') | Q(VaiTro__isnull=True) | Q(VaiTro=''))
    if user_role == 'ADMIN':
        role_queries |= Q(NguoiNhan__isnull=True, VaiTro__in=['ADMIN', 'BGH', 'TCM', 'GIAO_VIEN'])
    elif user_role == 'BGH':
        role_queries |= Q(NguoiNhan__isnull=True, VaiTro__in=['BGH', 'TCM'])
    elif user_role == 'TCM':
        role_queries |= Q(NguoiNhan__isnull=True, VaiTro__in=['TCM', 'GIAO_VIEN'])
    elif user_role == 'GIAO_VIEN':
        role_queries |= Q(NguoiNhan__isnull=True, VaiTro='GIAO_VIEN')

    unread_broadcast = ThongBao.objects.filter(role_queries).exclude(NguoiDaDoc=user)
    for tb in unread_broadcast:
        tb.NguoiDaDoc.add(user)

    return updated + unread_broadcast.count()

