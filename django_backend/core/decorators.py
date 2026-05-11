"""
自定义装饰器 - 核心模块
提供登录认证、权限检查等装饰器
"""
import functools
import logging
from django.http import JsonResponse
from django.conf import settings
from django.utils.decorators import method_decorator
from core.utils import error_response

logger = logging.getLogger('api')


def login_required(view_func):
    """
    登录认证装饰器
    从请求头 Authorization 中获取 JWT Token，验证用户身份
    验证通过后将 request.user_info 设置为用户信息字典
    用法: @login_required
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 从请求头获取 Token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return error_response("请先登录", code=401, status=401)
        
        # 使用 core.utils 中的 verify_jwt 验证
        from core.utils import verify_jwt
        payload = verify_jwt(auth_header)
        
        if not payload:
            return error_response("登录已过期，请重新登录", code=401, status=401)
        
        user_id = payload.get('user_id')
        if not user_id:
            return error_response("无效的认证信息", code=401, status=401)
        
        # 查询用户是否存在
        from users.models import User
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return error_response("用户不存在", code=401, status=401)
        
        # 检查用户状态
        if user.status == 'banned':
            return error_response("账号已被禁用", code=403, status=403)
        
        # 将用户信息附加到 request
        request.user_info = {
            'user_id': user.id,
            'openid': user.id,
            'nickname': user.nickname,
            'avatar': user.avatar,
            'is_member': user.is_member,
            'free_remaining': user.free_remaining,
            'is_admin': user.is_admin,
            'member_expire': user.member_expire.isoformat() if user.member_expire else None,
            'session_key': payload.get('session_key', ''),
        }
        
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """
    管理员权限装饰器
    要求用户已登录且是管理员
    用法: @admin_required (需要先使用 @login_required 或直接单独使用)
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 从请求头获取 Token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return error_response("请先登录", code=401, status=401)
        
        from core.utils import verify_jwt
        payload = verify_jwt(auth_header)
        
        if not payload:
            return error_response("登录已过期，请重新登录", code=401, status=401)
        
        user_id = payload.get('user_id')
        if not user_id:
            return error_response("无效的认证信息", code=401, status=401)
        
        from users.models import User
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return error_response("用户不存在", code=401, status=401)
        
        # 检查管理员权限
        if not user.is_admin:
            return error_response("无权访问，需要管理员权限", code=403, status=403)
        
        # 将用户信息附加到 request
        request.user_info = {
            'user_id': user.id,
            'openid': user.id,
            'nickname': user.nickname,
            'avatar': user.avatar,
            'is_member': user.is_member,
            'free_remaining': user.free_remaining,
            'is_admin': user.is_admin,
            'session_key': payload.get('session_key', ''),
        }
        
        return view_func(request, *args, **kwargs)
    return wrapper


def get_user_from_request(request):
    """
    从请求中获取用户信息（不强制登录，用于可选认证场景）
    :param request: Django HttpRequest
    :return: user 对象 或 None
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header:
        return None
    
    from core.utils import verify_jwt
    payload = verify_jwt(auth_header)
    
    if not payload:
        return None
    
    user_id = payload.get('user_id')
    if not user_id:
        return None
    
    from users.models import User
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None
