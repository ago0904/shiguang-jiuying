"""
用户模块 - URL 路由配置
所有路由以 /api/ 为前缀（在根urls.py中已配置）
"""
from django.urls import path
from . import views

urlpatterns = [
    # 微信登录
    path('auth/login', views.wechat_login, name='auth_login'),
    
    # 刷新 Token
    path('auth/refresh', views.refresh_token_view, name='auth_refresh'),
    
    # 获取用户信息
    path('auth/me', views.get_me, name='auth_me'),
    
    # 退出登录
    path('auth/logout', views.logout, name='auth_logout'),
    
    # 检查登录状态
    path('auth/check', views.check_login, name='auth_check'),
]
