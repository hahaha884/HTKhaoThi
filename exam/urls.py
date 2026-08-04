from django.urls import path
from . import views

urlpatterns = [
    path('', views.exam_list, name='exam_list'),
    path('tao-moi/', views.exam_wizard_start, name='exam_wizard_start'),
    path('<int:pk>/sua/', views.exam_editor, name='exam_editor'),
    path('<int:pk>/xoa/', views.exam_delete, name='exam_delete'),
    path('<int:pk>/xuat/<str:format>/', views.exam_export, name='exam_export'),
    path('api/get-matching-questions/', views.api_get_matching_questions, name='api_get_matching_questions'),
]
