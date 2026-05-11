"""
统计模块 - URL 路由配置
所有路由以 /api/stats/ 为前缀（在根urls.py中已配置）
"""
from django.urls import path
from . import views

urlpatterns = [
    # 数据看板（需管理员权限）
    path('dashboard', views.dashboard, name='stats_dashboard'),
    
    # 每日统计
    path('daily', views.daily_stats, name='stats_daily'),
    
    # 今日24小时统计
    path('hourly', views.hourly_stats, name='stats_hourly'),
    
    # 模式分布
    path('mode_distribution', views.mode_distribution, name='stats_mode'),
    
    # 平台分布
    path('platform_distribution', views.platform_distribution, name='stats_platform'),
]
