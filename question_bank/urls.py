from django.urls import path
from . import views

urlpatterns = [
    path('', views.question_list, name='question_list'),
    
    # Câu hỏi đơn
    path('them/', views.question_create, name='question_create'),
    path('<int:pk>/sua/', views.question_update, name='question_update'),
    path('<int:pk>/xoa/', views.question_delete, name='question_delete'),
    path('<int:pk>/preview/', views.question_preview, name='question_preview'),
    
    # Nhóm câu hỏi
    path('nhom/them/', views.group_create, name='group_create'),
    path('nhom/<int:pk>/sua/', views.group_update, name='group_update'),
    path('nhom/<int:pk>/xoa/', views.group_delete, name='group_delete'),
    
    # API endpoints lọc động
    path('api/mon-theo-khoi/', views.api_mon_theo_khoi, name='api_mon_theo_khoi'),
    path('api/mach-theo-mon-khoi/', views.api_mach_theo_mon_khoi, name='api_mach_theo_mon_khoi'),
    path('api/noidung-theo-mach/', views.api_noidung_theo_mach, name='api_noidung_theo_mach'),

    # Import Word & AI
    path('import-word/', views.import_word_preview, name='import_word_preview'),
    path('api/ai-suggest/', views.api_generate_ai_variations, name='api_ai_suggest'),
    path('api/ai-suggest-question/', views.api_suggest_question, name='api_suggest_question'),
    path('api/ai-suggest-group-content/', views.api_suggest_group_content, name='api_suggest_group_content'),
    path('save-imported/', views.save_imported_questions, name='save_imported'),
]
