"""管理后台路由配置

管理后台路由（以 /admin/ 为前缀）：
- /admin/          → 返回管理后台 HTML 页面
- /admin/api/*     → 管理后台API（需要 admin token）
"""
from django.urls import path
from . import views


urlpatterns = [
    # 管理后台页面
    path('', views.admin_page, name='admin_page'),
    
    # 认证API
    path('api/login', views.admin_login, name='admin_login'),
    path('api/check', views.admin_check, name='admin_check'),
    
    # 数据看板API
    path('api/dashboard', views.dashboard, name='admin_dashboard'),
    
    # 用户管理API
    path('api/users', views.user_list, name='admin_user_list'),
    path('api/users/<str:user_id>', views.user_detail, name='admin_user_detail'),
    path('api/users/<str:user_id>/status', views.user_status, name='admin_user_status'),
    path('api/users/<str:user_id>/member', views.user_member, name='admin_user_member'),
    path('api/users/<str:user_id>/history', views.user_history, name='admin_user_history'),
    
    # 修复记录API
    path('api/records', views.record_list, name='admin_record_list'),
    path('api/records/stats', views.record_stats, name='admin_record_stats'),
    
    # 系统设置API
    path('api/settings', views.get_settings, name='admin_get_settings'),
    path('api/settings/update', views.update_settings, name='admin_update_settings'),
    
    # 配额管理API
    path('api/quota', views.get_quota, name='admin_quota'),
]
