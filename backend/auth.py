"""微信登录认证模块

功能：
1. 微信小程序登录流程（code换openid）
2. JWT Token生成与验证
3. 用户自动注册/登录
4. 登录保护装饰器

API路由：
- POST /api/auth/login    - 微信登录
- POST /api/auth/refresh  - 刷新Token
- GET  /api/auth/me       - 获取当前用户信息
- POST /api/auth/logout   - 退出登录
"""

import uuid
import time
import logging
from functools import wraps
from datetime import datetime, timedelta

import jwt
import requests
from flask import Blueprint, request, g, jsonify

from config import Config
from models import user_dao, User

# ─────────────────────────────────────────────
# 日志
# ─────────────────────────────────────────────

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 创建蓝图
# ─────────────────────────────────────────────

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


# ─────────────────────────────────────────────
# 统一响应格式
# ─────────────────────────────────────────────


def success_response(data: dict = None, message: str = "成功"):
    """成功响应"""
    return jsonify({
        "code": 0,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time())
    })


def error_response(message: str, code: int = 1, status_code: int = 200):
    """错误响应"""
    response = jsonify({
        "code": code,
        "message": message,
        "data": {},
        "timestamp": int(time.time())
    })
    response.status_code = status_code
    return response


# ─────────────────────────────────────────────
# JWT Token 工具函数
# ─────────────────────────────────────────────


def create_token(user_id: str, **claims) -> str:
    """生成JWT Token

    Args:
        user_id: 用户ID (openid)
        **claims: 额外声明

    Returns:
        JWT Token字符串
    """
    now = datetime.utcnow()
    expire = now + timedelta(hours=Config.JWT_EXPIRE_HOURS)

    payload = {
        'iss': 'shiguang-jiuying',      # 签发者
        'sub': user_id,                  # 用户ID
        'iat': now,                      # 签发时间
        'exp': expire,                   # 过期时间
        'jti': str(uuid.uuid4()),        # 唯一ID
        **claims
    }

    token = jwt.encode(
        payload,
        Config.JWT_SECRET,
        algorithm=Config.JWT_ALGORITHM
    )

    return token


def verify_token(token: str) -> dict:
    """验证JWT Token

    Args:
        token: JWT Token字符串

    Returns:
        Token payload字典

    Raises:
        jwt.ExpiredSignatureError: Token已过期
        jwt.InvalidTokenError: Token无效
    """
    payload = jwt.decode(
        token,
        Config.JWT_SECRET,
        algorithms=[Config.JWT_ALGORITHM],
        options={'require': ['exp', 'sub']}
    )
    return payload


def decode_token_without_verify(token: str) -> dict:
    """仅解码Token（不验证签名和过期）

    用于登出等不需要验证的场景
    """
    try:
        payload = jwt.decode(
            token,
            options={'verify_signature': False, 'verify_exp': False}
        )
        return payload
    except Exception:
        return {}


# ─────────────────────────────────────────────
# 微信登录
# ─────────────────────────────────────────────


def wx_login(code: str) -> dict:
    """微信小程序登录

    通过code换取openid和session_key

    Args:
        code: 小程序前端获取的登录凭证

    Returns:
        dict: {openid, session_key, unionid}

    Raises:
        ValueError: 配置错误或微信接口返回错误
        requests.RequestException: 网络请求失败
    """
    # 检查配置
    if not Config.WECHAT_APPID or not Config.WECHAT_SECRET:
        logger.error("微信配置缺失: WECHAT_APPID 或 WECHAT_SECRET 未设置")
        raise ValueError("微信登录配置错误，请联系管理员")

    # 调用微信接口
    params = {
        'appid': Config.WECHAT_APPID,
        'secret': Config.WECHAT_SECRET,
        'js_code': code,
        'grant_type': 'authorization_code'
    }

    try:
        resp = requests.get(
            Config.WECHAT_JS_CODE_URL,
            params=params,
            timeout=10
        )
        resp.raise_for_status()
        result = resp.json()
    except requests.Timeout:
        logger.error("微信登录接口请求超时")
        raise ValueError("微信登录请求超时，请重试")
    except requests.RequestException as e:
        logger.error(f"微信登录接口请求失败: {e}")
        raise ValueError("微信登录请求失败，请重试")

    # 检查微信返回的错误
    if 'errcode' in result:
        errcode = result.get('errcode')
        errmsg = result.get('errmsg', '未知错误')
        logger.error(f"微信登录接口返回错误: errcode={errcode}, errmsg={errmsg}")

        error_map = {
            -1: "微信系统繁忙，请稍后再试",
            0: "请求成功",
            40029: "登录凭证(code)无效或已过期，请重新获取",
            40163: "登录凭证(code)已被使用，请重新获取",
            45009: "接口调用频率超出限制，请稍后再试",
            40226: "高风险等级用户，请引导用户处理风险",
        }
        raise ValueError(error_map.get(errcode, f"微信登录失败: {errmsg}"))

    openid = result.get('openid')
    if not openid:
        logger.error("微信接口未返回openid")
        raise ValueError("微信登录失败，未获取到用户信息")

    return {
        'openid': openid,
        'session_key': result.get('session_key', ''),
        'unionid': result.get('unionid', '')
    }


# ─────────────────────────────────────────────
# 用户注册/登录
# ─────────────────────────────────────────────


def register_or_login(openid: str, union_id: str = "", user_info: dict = None) -> dict:
    """用户注册或登录

    新用户自动注册，老用户更新登录时间

    Args:
        openid: 微信openid
        union_id: 微信unionid
        user_info: 用户信息字典 {nickName, avatarUrl, ...}

    Returns:
        dict: {token, user_info}
    """
    user_info = user_info or {}
    nickname = user_info.get('nickName', '') or user_info.get('nickname', '')
    avatar = user_info.get('avatarUrl', '') or user_info.get('avatar', '')

    # 查找用户
    user = user_dao.get_by_id(openid)

    if user:
        # 老用户 - 更新登录时间
        user.last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 更新用户信息（如果提供了新的）
        if nickname:
            user.nickname = nickname
        if avatar:
            user.avatar = avatar
        if union_id and not user.union_id:
            user.union_id = union_id

        user_dao.save(user)
        logger.info(f"用户登录: {openid}, 昵称: {user.nickname}")
    else:
        # 新用户注册
        user = user_dao.create(
            user_id=openid,
            union_id=union_id,
            nickname=nickname,
            avatar=avatar
        )
        logger.info(f"新用户注册: {openid}, 昵称: {nickname}")

    # 生成Token
    token = create_token(
        user_id=user.id,
        nickname=user.nickname,
        avatar=user.avatar,
        is_admin=user.is_admin
    )

    return {
        'token': token,
        'user_info': {
            'id': user.id,
            'nickname': user.nickname,
            'avatar': user.avatar,
            'free_remaining': user.free_remaining,
            'is_member': user.is_member_valid(),
            'is_admin': user.is_admin,
            'total_repairs': user.total_repairs,
            'created_at': user.created_at
        }
    }


# ─────────────────────────────────────────────
# 装饰器
# ─────────────────────────────────────────────


def login_required(f):
    """登录保护装饰器

    要求请求头中包含有效的Authorization: Bearer <token>

    验证成功后，将用户信息存入 g.current_user
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取Token
        auth_header = request.headers.get('Authorization', '')
        token = ''

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        elif auth_header.startswith('bearer '):
            token = auth_header[7:]

        if not token:
            return error_response("请先登录", code=401, status_code=401)

        try:
            # 验证Token
            payload = verify_token(token)
            user_id = payload.get('sub')

            if not user_id:
                return error_response("Token无效", code=401, status_code=401)

            # 获取用户
            user = user_dao.get_by_id(user_id)
            if not user:
                return error_response("用户不存在", code=401, status_code=401)

            if not user.is_active():
                return error_response("账号已被禁用", code=403, status_code=403)

            # 存入全局
            g.current_user = user
            g.token_payload = payload

            return f(*args, **kwargs)

        except jwt.ExpiredSignatureError:
            logger.warning("Token已过期")
            return error_response("登录已过期，请重新登录", code=401, status_code=401)
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token验证失败: {e}")
            return error_response("登录状态无效，请重新登录", code=401, status_code=401)
        except Exception as e:
            logger.error(f"认证处理异常: {e}")
            return error_response("认证处理异常", code=500, status_code=500)

    return decorated_function


def admin_required(f):
    """管理员权限装饰器

    在 login_required 基础上，要求用户是管理员
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 先执行登录验证
        auth_header = request.headers.get('Authorization', '')
        token = ''

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        elif auth_header.startswith('bearer '):
            token = auth_header[7:]

        if not token:
            return error_response("请先登录", code=401, status_code=401)

        try:
            payload = verify_token(token)
            user_id = payload.get('sub')

            if not user_id:
                return error_response("Token无效", code=401, status_code=401)

            user = user_dao.get_by_id(user_id)
            if not user:
                return error_response("用户不存在", code=401, status_code=401)

            if not user.is_active():
                return error_response("账号已被禁用", code=403, status_code=403)

            # 检查管理员权限
            if not user.is_admin:
                return error_response("无管理员权限", code=403, status_code=403)

            g.current_user = user
            g.token_payload = payload

            return f(*args, **kwargs)

        except jwt.ExpiredSignatureError:
            return error_response("登录已过期", code=401, status_code=401)
        except jwt.InvalidTokenError:
            return error_response("登录状态无效", code=401, status_code=401)
        except Exception as e:
            logger.error(f"管理员认证异常: {e}")
            return error_response("认证异常", code=500, status_code=500)

    return decorated_function


# ─────────────────────────────────────────────
# API路由
# ─────────────────────────────────────────────


@auth_bp.route('/login', methods=['POST'])
def login():
    """微信登录接口

    请求体:
        {
            "code": "小程序登录凭证",
            "userInfo": {          # 可选
                "nickName": "昵称",
                "avatarUrl": "头像URL"
            }
        }

    响应:
        {
            "code": 0,
            "message": "登录成功",
            "data": {
                "token": "JWT Token",
                "user_info": {
                    "id": "openid",
                    "nickname": "昵称",
                    "avatar": "头像URL",
                    "free_remaining": 3,
                    "is_member": false,
                    "is_admin": false,
                    "total_repairs": 0,
                    "created_at": "2024-01-01 00:00:00"
                }
            },
            "timestamp": 1700000000
        }
    """
    try:
        data = request.get_json(silent=True) or {}

        # 获取code
        code = data.get('code', '')
        if not code:
            return error_response("缺少code参数", code=400, status_code=400)

        # 调用微信登录
        try:
            wx_result = wx_login(code)
        except ValueError as e:
            return error_response(str(e), code=400)
        except Exception as e:
            logger.error(f"微信登录异常: {e}")
            return error_response("微信登录失败，请重试", code=500)

        openid = wx_result['openid']
        union_id = wx_result.get('unionid', '')

        # 获取用户信息（可选）
        user_info = data.get('userInfo', {})

        # 注册或登录
        result = register_or_login(openid, union_id, user_info)

        return success_response(result, message="登录成功")

    except Exception as e:
        logger.error(f"登录接口异常: {e}", exc_info=True)
        return error_response("登录失败，请稍后重试", code=500)


@auth_bp.route('/refresh', methods=['POST'])
@login_required
def refresh_token():
    """刷新Token接口

    使用当前有效Token换取新的Token

    请求头:
        Authorization: Bearer <当前Token>

    响应:
        {
            "code": 0,
            "message": "刷新成功",
            "data": {
                "token": "新的JWT Token"
            },
            "timestamp": 1700000000
        }
    """
    try:
        user = g.current_user

        # 生成新Token
        new_token = create_token(
            user_id=user.id,
            nickname=user.nickname,
            avatar=user.avatar,
            is_admin=user.is_admin
        )

        return success_response({
            'token': new_token
        }, message="刷新成功")

    except Exception as e:
        logger.error(f"刷新Token异常: {e}")
        return error_response("刷新Token失败", code=500)


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_me():
    """获取当前用户信息

    请求头:
        Authorization: Bearer <Token>

    响应:
        {
            "code": 0,
            "message": "成功",
            "data": {
                "id": "openid",
                "nickname": "昵称",
                "avatar": "头像URL",
                "free_remaining": 3,
                "is_member": false,
                "is_admin": false,
                "total_repairs": 0,
                "created_at": "2024-01-01 00:00:00",
                "last_login": "2024-01-01 12:00:00"
            },
            "timestamp": 1700000000
        }
    """
    try:
        user = g.current_user

        user_data = {
            'id': user.id,
            'nickname': user.nickname,
            'avatar': user.avatar,
            'free_remaining': user.free_remaining,
            'is_member': user.is_member_valid(),
            'is_admin': user.is_admin,
            'total_repairs': user.total_repairs,
            'created_at': user.created_at,
            'last_login': user.last_login
        }

        return success_response(user_data, message="成功")

    except Exception as e:
        logger.error(f"获取用户信息异常: {e}")
        return error_response("获取用户信息失败", code=500)


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """退出登录接口

    客户端需要自行清除本地Token
    后端记录登出日志（可选做Token黑名单）

    请求头:
        Authorization: Bearer <Token>

    响应:
        {
            "code": 0,
            "message": "已退出登录",
            "data": {},
            "timestamp": 1700000000
        }
    """
    try:
        user = g.current_user
        logger.info(f"用户退出登录: {user.id}, 昵称: {user.nickname}")

        return success_response(message="已退出登录")

    except Exception as e:
        logger.error(f"退出登录异常: {e}")
        return error_response("操作失败", code=500)


@auth_bp.route('/check', methods=['GET'])
def check_auth():
    """检查登录状态（无需登录）

    用于前端检查Token是否仍然有效

    请求头:
        Authorization: Bearer <Token>

    响应:
        {
            "code": 0,
            "message": "登录有效",
            "data": {"valid": true},
            "timestamp": 1700000000
        }
    """
    auth_header = request.headers.get('Authorization', '')
    token = ''

    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    elif auth_header.startswith('bearer '):
        token = auth_header[7:]

    if not token:
        return success_response({"valid": False}, message="未登录")

    try:
        verify_token(token)
        return success_response({"valid": True}, message="登录有效")
    except jwt.ExpiredSignatureError:
        return success_response({"valid": False}, message="登录已过期")
    except jwt.InvalidTokenError:
        return success_response({"valid": False}, message="登录状态无效")
    except Exception as e:
        logger.error(f"检查登录状态异常: {e}")
        return error_response("检查失败", code=500)
