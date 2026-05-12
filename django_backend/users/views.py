"""
用户模块 - API 视图
提供微信登录、Token刷新、用户信息查询等接口
"""
import json
import time
import logging
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from core.utils import (
    success_response, error_response,
    create_jwt, create_refresh_token, verify_jwt, verify_refresh_token,
    call_wechat_jscode2session,
    get_client_ip
)
from core.decorators import login_required
from users.models import User

logger = logging.getLogger('users')


# ============================================================
# 1. 微信登录
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def wechat_login(request):
    """
    POST /api/auth/login
    微信小程序登录
    请求参数:
        - code: 微信小程序登录凭证 (必填)
        - user_info: 用户信息 (可选, JSON对象)
        - invite_code: 邀请码 (可选)
    返回:
        - token: JWT访问令牌
        - refresh_token: JWT刷新令牌
        - expires_in: token有效期(秒)
        - user_info: 用户信息
    """
    try:
        client_ip = get_client_ip(request)
        logger.info(f"[Login] 收到登录请求 from {client_ip}")
        
        # 解析请求体
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return error_response("请求参数必须是JSON格式", code=400, status=400)
        
        code = body.get('code')
        user_info_data = body.get('user_info') or body.get('userInfo') or {}
        invite_code = body.get('invite_code', '')
        
        # 参数校验
        if not code:
            return error_response("缺少 code 参数", code=400, status=400)
        
        # 检查小程序配置
        appid = settings.WECHAT_APPID
        secret = settings.WECHAT_SECRET
        
        if not appid or not secret:
            logger.warning("[Login] 微信小程序配置未设置，使用模拟登录模式")
            return mock_login(code, user_info_data, client_ip)
        
        # 调用微信接口
        logger.info(f"[Login] 调用微信 jscode2session, appid={appid[:8]}...")
        wx_data = call_wechat_jscode2session(appid, secret, code)
        
        if not wx_data:
            return error_response("微信登录接口调用失败", code=500)
        
        # 检查微信返回的错误
        if 'errcode' in wx_data and wx_data['errcode'] != 0:
            err_msg = wx_data.get('errmsg', '未知微信错误')
            logger.warning(f"[Login] 微信返回错误: {err_msg}")
            return error_response(f"微信登录失败: {err_msg}", code=400, status=400)
        
        openid = wx_data.get('openid')
        session_key = wx_data.get('session_key', '')
        unionid = wx_data.get('unionid', '')
        
        if not openid:
            logger.error("[Login] 微信未返回 openid")
            return error_response("微信登录失败，未获取到用户标识", code=500)
        
        logger.info(f"[Login] 微信返回 openid={openid[:16]}..., unionid={unionid[:16] if unionid else 'None'}")
        
        # 查询或创建用户
        user, created = User.objects.get_or_create(
            pk=openid,
            defaults={
                'union_id': unionid,
                'free_remaining': 3,  # 新用户3次免费
            }
        )
        
        # 如果是新用户
        if created:
            logger.info(f"[Login] 新用户注册: {openid[:16]}...")
            # 更新用户信息
            if user_info_data:
                _update_user_info(user, user_info_data)
            user.ip = client_ip
            user.save()
        else:
            logger.info(f"[Login] 老用户登录: {openid[:16]}...")
            # 更新用户信息
            if user_info_data:
                _update_user_info(user, user_info_data)
            if unionid and not user.union_id:
                user.union_id = unionid
            user.session_key = session_key
            user.save()
        
        # 生成 JWT Token
        token = create_jwt(
            user_id=openid,
            session_key=session_key,
            nickname=user.nickname,
        )
        refresh_token = create_refresh_token(openid)
        
        logger.info(f"[Login] 登录成功: {openid[:16]}..., 新用户={created}")
        
        return success_response(data={
            "token": token,
            "refresh_token": refresh_token,
            "expires_in": settings.JWT_EXPIRE_HOURS * 3600,
            "token_type": "Bearer",
            "is_new_user": created,
            "user_info": user.to_dict()
        }, message="登录成功")
    
    except Exception as e:
        logger.error(f"[Login] 登录异常: {e}", exc_info=True)
        return error_response(f"登录失败: {str(e)}", code=500)


def mock_login(code, user_info_data, client_ip):
    """
    模拟登录（开发测试用，不依赖微信配置）
    """
    try:
        # 使用 code 生成 mock openid
        import hashlib
        mock_openid = f"mock_{hashlib.md5(code.encode()).hexdigest()[:28]}"
        
        user, created = User.objects.get_or_create(
            pk=mock_openid,
            defaults={
                'union_id': '',
                'free_remaining': 3,
            }
        )
        
        if created:
            if user_info_data:
                _update_user_info(user, user_info_data)
            user.save()
        
        token = create_jwt(user_id=mock_openid, mock=True)
        refresh_token = create_refresh_token(mock_openid)
        
        logger.info(f"[Login] 模拟登录成功: {mock_openid[:16]}...")
        
        return success_response(data={
            "token": token,
            "refresh_token": refresh_token,
            "expires_in": settings.JWT_EXPIRE_HOURS * 3600,
            "token_type": "Bearer",
            "is_new_user": created,
            "user_info": user.to_dict(),
            "note": "模拟登录模式"
        }, message="模拟登录成功")
    except Exception as e:
        logger.error(f"[Login] 模拟登录失败: {e}")
        return error_response(f"登录失败: {str(e)}", code=500)


def _update_user_info(user, user_info):
    """
    更新用户信息
    """
    if isinstance(user_info, str):
        try:
            user_info = json.loads(user_info)
        except json.JSONDecodeError:
            return
    
    if not isinstance(user_info, dict):
        return
    
    nickname = user_info.get('nickName') or user_info.get('nickname', '')
    avatar = user_info.get('avatarUrl') or user_info.get('avatar', '')
    
    if nickname and not user.nickname:
        user.nickname = nickname[:100]
    if avatar and not user.avatar:
        user.avatar = avatar[:500]
    
    user.raw_data = json.dumps(user_info, ensure_ascii=False)[:2000]


# ============================================================
# 2. 刷新 Token
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def refresh_token_view(request):
    """
    POST /api/auth/refresh
    刷新 JWT Token
    请求参数:
        - refresh_token: 刷新令牌 (必填)
    返回:
        - token: 新的 JWT 访问令牌
        - expires_in: 新的有效期
    """
    try:
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return error_response("请求参数必须是JSON格式", code=400, status=400)
        
        refresh_token = body.get('refresh_token')
        if not refresh_token:
            return error_response("缺少 refresh_token 参数", code=400, status=400)
        
        # 验证刷新 token
        payload = verify_refresh_token(refresh_token)
        if not payload:
            logger.warning("[Refresh] 刷新Token无效或已过期")
            return error_response("刷新令牌无效或已过期，请重新登录", code=401, status=401)
        
        user_id = payload.get('user_id')
        
        # 检查用户是否存在
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return error_response("用户不存在", code=404, status=404)
        
        if user.status == 'banned':
            return error_response("账号已被禁用", code=403, status=403)
        
        # 生成新的访问 token
        new_token = create_jwt(
            user_id=user_id,
            nickname=user.nickname,
        )
        new_refresh_token = create_refresh_token(user_id)
        
        logger.info(f"[Refresh] Token刷新成功: {user_id[:16]}...")
        
        return success_response(data={
            "token": new_token,
            "refresh_token": new_refresh_token,
            "expires_in": settings.JWT_EXPIRE_HOURS * 3600,
            "token_type": "Bearer",
        }, message="刷新成功")
    
    except Exception as e:
        logger.error(f"[Refresh] Token刷新异常: {e}", exc_info=True)
        return error_response(f"刷新失败: {str(e)}", code=500)


# ============================================================
# 3. 获取当前用户信息
# ============================================================

@require_http_methods(["GET"])
@login_required
def get_me(request):
    """
    GET /api/auth/me
    获取当前登录用户信息
    需要在请求头中携带 Authorization: Bearer <token>
    """
    try:
        user_info = request.user_info
        user_id = user_info['user_id']
        
        logger.info(f"[Me] 获取用户信息: {user_id[:16]}...")
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return error_response("用户不存在", code=404, status=404)
        
        return success_response(data={
            "user_info": user.to_dict()
        }, message="获取成功")
    
    except Exception as e:
        logger.error(f"[Me] 获取用户信息失败: {e}", exc_info=True)
        return error_response(f"获取用户信息失败: {str(e)}", code=500)


# ============================================================
# 4. 退出登录
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def logout(request):
    """
    POST /api/auth/logout
    退出登录
    服务端记录退出日志（JWT无状态，客户端需自行清除token）
    """
    try:
        user_info = request.user_info
        user_id = user_info['user_id']
        
        logger.info(f"[Logout] 用户退出登录: {user_id[:16]}...")
        
        # 可以在这里做服务端token黑名单等处理
        # 当前JWT是无状态的，主要靠客户端清除
        
        return success_response(message="退出成功")
    
    except Exception as e:
        logger.error(f"[Logout] 退出失败: {e}", exc_info=True)
        return error_response(f"退出失败: {str(e)}", code=500)


# ============================================================
# 5. 检查登录状态
# ============================================================

@require_http_methods(["GET"])
def check_login(request):
    """
    GET /api/auth/check
    检查当前登录状态
    无需强制登录，有token则返回用户信息，无token则返回未登录
    """
    try:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return success_response(data={
                "is_login": False,
                "user_info": None
            }, message="未登录")
        
        # 验证 token
        from core.utils import verify_jwt
        payload = verify_jwt(auth_header)
        
        if not payload:
            return success_response(data={
                "is_login": False,
                "user_info": None
            }, message="登录已过期")
        
        user_id = payload.get('user_id')
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return success_response(data={
                "is_login": False,
                "user_info": None
            }, message="用户不存在")
        
        if user.status == 'banned':
            return success_response(data={
                "is_login": False,
                "user_info": None
            }, message="账号已被禁用")
        
        return success_response(data={
            "is_login": True,
            "user_info": user.to_dict()
        }, message="已登录")
    
    except Exception as e:
        logger.error(f"[Check] 检查登录状态失败: {e}", exc_info=True)
        return success_response(data={
            "is_login": False,
            "user_info": None
        }, message=f"检查失败: {str(e)}")
