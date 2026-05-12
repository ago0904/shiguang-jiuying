"""
API 模块 - URL 路由配置
所有路由以 /api/ 为前缀
"""
from django.urls import path
from . import views

urlpatterns = [
    # 上传图片
    path('upload', views.upload_image, name='upload'),
    
    # 修复图片（需登录）
    path('repair', views.repair_image, name='repair'),
    
    # 获取结果图片
    path('result/<str:file_id>', views.get_result, name='result'),
    
    # 获取上传的原图
    path('image/<str:file_id>', views.get_uploaded_image, name='image'),
    
    # 修复历史（需登录）
    path('history', views.get_history, name='history'),
    
    # 删除记录（需登录）
    path('history/<str:history_id>', views.delete_history, name='delete_history'),
    
    # 获取配额（需登录）
    path('quota', views.get_quota, name='quota'),
]
