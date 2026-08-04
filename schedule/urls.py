from django.urls import path
from . import views
from . import views_assignment

urlpatterns = [
    path('', views.schedule_list, name='schedule_list'),
    path('tao/buoc-1/', views.schedule_create_step1, name='schedule_create_step1'),
    path('tao/buoc-2/', views.schedule_create_step2, name='schedule_create_step2'),
    path('<int:pk>/sua/buoc-1/', views.schedule_edit_step1, name='schedule_edit_step1'),
    path('sua/buoc-2/', views.schedule_edit_step2, name='schedule_edit_step2'),
    path('<int:pk>/xoa/', views.schedule_delete, name='schedule_delete'),
    path('api/mon-theo-khoi/', views.schedule_api_mon_theo_khoi, name='schedule_api_mon_theo_khoi'),
    
    # URL cho phân công giám thị
    path('phan-cong/', views_assignment.assignment_list, name='assignment_list'),
    path('phan-cong/tu-dong/cauhinh/', views_assignment.assignment_auto_config, name='assignment_auto_config'),
    path('phan-cong/tu-dong/xem-truoc/', views_assignment.assignment_auto_preview, name='assignment_auto_preview'),
    path('phan-cong/<int:pk>/sua/', views_assignment.assignment_edit, name='assignment_edit'),
    path('phan-cong/<int:pk>/xoa/', views_assignment.assignment_delete, name='assignment_delete'),
]
