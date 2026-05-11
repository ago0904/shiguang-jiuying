"""微信登录认证"""
import requests
import logging
from django.conf import settings
from .utils import create_jwt, json_response, error_response
from users.models import User

logger = logging.getLogger(__name__)


def wx_login(code):
    """调用微信API换取openid
    
    通过微信小程序登录凭证code换取openid和session_key。
    
    Args:
        code: 小程序前端获取的登录凭证
        
    Returns:
        (success: bool, data: dict or str)
        成功时返回 (True, {'openid': ..., 'session_key': ..., 'unionid': ...})
        失败时返回 (False, '错误信息')
    """
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        'appid': settings.WECHAT_APPID,
        'secret': settings.WECHAT_SECRET,
        'js_code': code,
        'grant_type': 'authorization_code'
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if 'openid' in data:
            logger.info(f"微信登录成功: openid={data['openid'][:16]}...")
            return True, data  # {'openid', 'session_key', 'unionid'}
        errcode = data.get('errcode', 'unknown')
        errmsg = data.get('errmsg', '微信登录失败')
        logger.warning(f"微信登录失败: errcode={errcode}, errmsg={errmsg}")
        return False, errmsg
    except requests.Timeout:
        logger.error("微信登录接口请求超时")
        return False, "微信登录请求超时，请重试"
    except requests.RequestException as e:
        logger.error(f"微信登录接口请求失败: {e}")
        return False, f"微信登录请求失败: {str(e)}"
    except Exception as e:
        logger.error(f"微信登录异常: {e}")
        return False, str(e)


def register_or_login(openid, union_id='', nickname='', avatar=''):
    """注册或登录用户
    
    如果用户已存在则更新信息，不存在则创建新用户。
    
    Args:
        openid: 微信openid
        union_id: 微信unionid
        nickname: 用户昵称
        avatar: 用户头像URL
        
    Returns:
        User: 用户对象
    """
    try:
        user = User.objects.get(pk=openid)
        # 更新信息
        updated = False
        if nickname and nickname != user.nickname:
            user.nickname = nickname
            updated = True
        if avatar and avatar != user.avatar:
            user.avatar = avatar
            updated = True
        if union_id and not user.union_id:
            user.union_id = union_id
            updated = True
        if updated:
            user.save()
            logger.info(f"用户信息更新: {openid[:16]}...")
    except User.DoesNotExist:
        # 新用户注册
        free_repairs = getattr(settings, 'FREE_REPAIRS', 3)
        user = User.objects.create(
            id=openid,
            union_id=union_id,
            nickname=nickname,
            avatar=avatar,
            free_remaining=free_repairs,
            status='active'
        )
        logger.info(f"新用户注册: {openid[:16]}..., 昵称: {nickname}")
    return user


def wx_login_view(request):
    """微信登录视图
    
    处理微信小程序登录请求:
    1. 接收前端传来的code
    2. 调用微信API换取openid
    3. 注册或登录用户
    4. 生成JWT Token返回给前端
    
    POST /api/auth/login
    Body: {"code": "xxx", "nickname": "xxx", "avatar": "xxx"}
    """
    import json
    from django.views.decorators.http import require_http_methods
    from django.views.decorators.csrf import csrf_exempt
    
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return error_response("请求格式错误", code=400)
    
    code = body.get('code', '').strip()
    nickname = body.get('nickname', '').strip()
    avatar = body.get('avatar', '').strip()
    
    if not code:
        return error_response("缺少code参数", code=400)
    
    # 检查微信配置
    if not settings.WECHAT_APPID or not settings.WECHAT_SECRET:
        logger.error("微信配置缺失: WECHAT_APPID 或 WECHAT_SECRET 未设置")
        return error_response("微信登录配置错误，请联系管理员", code=500)
    
    # 调用微信登录
    success, result = wx_login(code)
    if not success:
        return error_response(result, code=401)
    
    openid = result.get('openid')
    union_id = result.get('unionid', '')
    
    # 注册或登录用户
    user = register_or_login(openid, union_id=union_id, nickname=nickname, avatar=avatar)
    
    # 检查用户状态
    if not user.is_active_user():
        return error_response("账号已被禁用", code=403)
    
    # 生成JWT Token
    token = create_jwt(
        user_id=user.id,
        nickname=user.nickname,
        avatar=user.avatar
    )
    
    return json_response(data={
        'token': token,
        'user_id': user.id,
        'nickname': user.nickname,
        'avatar': user.avatar,
        'free_remaining': user.free_remaining,
        'is_member': user.is_member and user.is_member_valid(),
        'member_expire': user.member_expire.strftime('%Y-%m-%d') if user.member_expire else None,
    }, message="登录成功")


def refresh_token_view(request):
    """刷新Token视图
    
    POST /api/auth/refresh
    Header: Authorization: Bearer <old_token>
    """
    from .decorators import login_required
    
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return error_response("缺少Token", code=401)
    
    old_token = auth_header[7:]
    payload = verify_jwt(old_token)
    if not payload:
        return error_response("Token已过期", code=401)
    
    user_id = payload.get('user_id')
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return error_response("用户不存在", code=404)
    
    # 生成新Token
    new_token = create_jwt(
        user_id=user.id,
        nickname=user.nickname,
        avatar=user.avatar
    )
    
    return json_response(data={
        'token': new_token,
        'user_id': user.id,
        'nickname': user.nickname,
        'avatar': user.avatar,
    }, message="刷新成功")


def get_user_info_view(request):
    """获取当前用户信息视图
    
    GET /api/auth/me
    Header: Authorization: Bearer <token>
    """
    from .decorators import login_required
    
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return error_response("请先登录", code=401)
    
    token = auth_header[7:]
    payload = verify_jwt(token)
    if not payload:
        return error_response("登录已过期", code=401)
    
    user_id = payload.get('user_id')
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return error_response("用户不存在", code=404)
    
    return json_response(data=user.to_dict())
