from django.urls import path
from . import views

urlpatterns = [
    path('', views.schedule_list, name='schedule_list'),
    path('tao/buoc-1/', views.schedule_create_step1, name='schedule_create_step1'),
    path('tao/buoc-2/', views.schedule_create_step2, name='schedule_create_step2'),
    path('<int:pk>/sua/buoc-1/', views.schedule_edit_step1, name='schedule_edit_step1'),
    path('sua/buoc-2/', views.schedule_edit_step2, name='schedule_edit_step2'),
    path('<int:pk>/xoa/', views.schedule_delete, name='schedule_delete'),
    path('api/mon-theo-khoi/', views.schedule_api_mon_theo_khoi, name='schedule_api_mon_theo_khoi'),
]
