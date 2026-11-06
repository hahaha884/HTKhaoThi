from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from core.views_dashboard import dashboard
from core import views_notification

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('core.urls')),
    path('ma-tran/', include('matrix.urls')),
    path('de-thi/', include('exam.urls')),
    path('lich-thi/', include('schedule.urls')),
    path('cau-hoi/', include('question_bank.urls')), 
    
    # Notifications (Thông báo)
    path('thong-bao/', views_notification.notification_list_view, name='notification_list'),
    path('thong-bao/api/', views_notification.api_get_notifications, name='api_notifications'),
    path('thong-bao/api/<int:pk>/doc/', views_notification.api_mark_read, name='api_notification_mark_read'),
    path('thong-bao/api/doc-tat-ca/', views_notification.api_mark_all_read, name='api_notification_mark_all_read'),

    path('', dashboard, name='dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
