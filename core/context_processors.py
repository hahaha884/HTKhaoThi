from core.notification_service import get_user_notifications

def notifications_context(request):
    """
    Context processor cung cấp dữ liệu thông báo cho mọi template (base.html và các trang con).
    """
    if not request.user.is_authenticated:
        return {
            'nav_notifications': [],
            'unread_notifications_count': 0,
            'total_notifications_count': 0,
        }

    try:
        data = get_user_notifications(request.user, limit=15)
        return {
            'nav_notifications': data['notifications'],
            'unread_notifications_count': data['unread_count'],
            'total_notifications_count': data['total_count'],
        }
    except Exception:
        return {
            'nav_notifications': [],
            'unread_notifications_count': 0,
            'total_notifications_count': 0,
        }

