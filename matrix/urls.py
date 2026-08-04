from django.urls import path
from . import views

urlpatterns = [
    path('', views.matrix_list, name='matrix_list'),
    path('them/', views.matrix_create, name='matrix_create'),
    path('<int:pk>/sua/', views.matrix_update, name='matrix_update'),
    path('<int:pk>/xoa/', views.matrix_delete, name='matrix_delete'),
    path('<int:pk>/', views.matrix_detail, name='matrix_detail'),
    path('<int:pk>/duyet/', views.matrix_approve, name='matrix_approve'),
    path('<int:pk>/xuat/', views.matrix_export, name='matrix_export'),
]
