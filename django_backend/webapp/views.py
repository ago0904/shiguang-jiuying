"""
Web前端视图 - H5照片修复页面
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import time


def index(request):
    """H5照片修复首页"""
    return render(request, 'webapp/index.html', {
        'api_base': '',  # 使用相对路径
    })


@csrf_exempt
@require_http_methods(["GET"])
def webapp_config(request):
    """获取前端配置"""
    return JsonResponse({
        "code": 0,
        "message": "成功",
        "data": {
            "api_base": "/api",
            "max_file_size": 20 * 1024 * 1024,  # 20MB
            "allowed_types": ["image/jpeg", "image/png", "image/bmp", "image/webp"],
            "modes": [
                {"key": "colorize", "name": "黑白上色", "icon": "🎨", "color": "#C47B5A",
                 "desc": "为黑白照片注入自然色彩"},
                {"key": "repair", "name": "破损修复", "icon": "🔧", "color": "#7A9E7E",
                 "desc": "智能填补破损与划痕"},
                {"key": "enhance", "name": "清晰度增强", "icon": "✨", "color": "#D4A35A",
                 "desc": "模糊照片变清晰"},
                {"key": "denoise", "name": "智能去噪", "icon": "🌿", "color": "#7E8FA3",
                 "desc": "去除噪点保留细节"},
            ]
        },
        "timestamp": int(time.time())
    })
