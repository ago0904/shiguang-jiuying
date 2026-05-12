"""
时光修复项目 - 根路由配置
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django 默认管理后台
    path('django-admin/', admin.site.urls),
    
    # 管理后台（自定义）
    path('admin/', include('admin_portal.urls')),
    
    # API 路由 - 以 /api/ 为前缀
    path('api/', include('users.urls')),       # /api/auth/*
    path('api/', include('api.urls')),         # /api/upload, /api/repair 等
    path('api/stats/', include('stats.urls')), # /api/stats/*
    
    # Web 前端 - H5照片修复页面
    path('webapp/', include('webapp.urls')),   # /webapp/
]

# 开发环境提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
