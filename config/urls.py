from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from core.views_dashboard import dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('core.urls')),
    path('ma-tran/', include('matrix.urls')),
    path('de-thi/', include('exam.urls')),
    path('lich-thi/', include('schedule.urls')),
    path('cau-hoi/', include('question_bank.urls')), 
    path('', dashboard, name='dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
