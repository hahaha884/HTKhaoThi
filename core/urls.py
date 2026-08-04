from django.urls import path
from . import views_auth, views_teacher, views_account, views_schoolyear, views_subject, views_class

urlpatterns = [
    # Auth
    path('login/', views_auth.login_view, name='login'),
    path('doi-mat-khau-lan-dau/', views_auth.change_password_first_login, name='change_password_first_login'),
    path('logout/', views_auth.logout_view, name='logout'),
    path('tao-to-2/', views_auth.tao_to2, name='tao_to2'),
    
    # Teacher Management
    path('giao-vien/', views_teacher.teacher_list, name='teacher_list'),
    path('giao-vien/them/', views_teacher.teacher_create, name='teacher_create'),
    path('giao-vien/import/', views_teacher.teacher_import, name='teacher_import'),
    path('giao-vien/<int:pk>/sua/', views_teacher.teacher_update, name='teacher_update'),
    path('giao-vien/<int:pk>/xoa/', views_teacher.teacher_delete, name='teacher_delete'),

    # Account Management
    path('tai-khoan/', views_account.account_list, name='account_list'),
    path('tai-khoan/them/', views_account.account_create, name='account_create'),
    path('tai-khoan/<int:pk>/sua/', views_account.account_update, name='account_update'),
    path('tai-khoan/<int:pk>/xoa/', views_account.account_delete, name='account_delete'),

    # School Year Management
    path('nam-hoc/', views_schoolyear.schoolyear_list, name='schoolyear_list'),
    path('nam-hoc/them/', views_schoolyear.schoolyear_create, name='schoolyear_create'),
    path('nam-hoc/<int:pk>/sua/', views_schoolyear.schoolyear_update, name='schoolyear_update'),
    path('nam-hoc/<int:pk>/xoa/', views_schoolyear.schoolyear_delete, name='schoolyear_delete'),

    # Subject Management
    path('mon-hoc/', views_subject.subject_list, name='subject_list'),
    path('mon-hoc/them/', views_subject.subject_create, name='subject_create'),
    path('mon-hoc/<int:pk>/sua/', views_subject.subject_update, name='subject_update'),
    path('mon-hoc/<int:pk>/xoa/', views_subject.subject_delete, name='subject_delete'),

    # Class Management
    path('lop-hoc/', views_class.class_list, name='class_list'),
    path('lop-hoc/them/', views_class.class_create, name='class_create'),
    path('lop-hoc/<int:pk>/sua/', views_class.class_update, name='class_update'),
    path('lop-hoc/<int:pk>/xoa/', views_class.class_delete, name='class_delete'),
]


