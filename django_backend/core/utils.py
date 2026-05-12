"""
通用工具函数 - 核心模块
提供统一的 JSON 响应、JWT 生成与验证、文件处理等
"""
import time
import json
import hashlib
import base64
import uuid
import os
import re
import logging
from pathlib import Path
from django.http import JsonResponse, FileResponse, HttpResponse
from django.conf import settings
from datetime import datetime, timedelta

logger = logging.getLogger('api')

# ============================================================
# 统一 JSON 响应格式
# ============================================================

def json_response(data=None, message="操作成功", code=0, status=200):
    """
    统一 JSON 响应格式
    返回: {"code": int, "message": str, "data": dict, "timestamp": int}
    """
    return JsonResponse({
        "code": code,
        "message": message,
        "data": data if data is not None else {},
        "timestamp": int(time.time())
    }, status=status, json_dumps_params={'ensure_ascii': False})


def error_response(message="操作失败", code=500, status=500):
    """统一错误响应"""
    logger.error(f"[ErrorResponse] code={code}, message={message}")
    return json_response(message=message, code=code, status=status)


def success_response(data=None, message="操作成功"):
    """统一成功响应"""
    return json_response(data=data, message=message, code=0, status=200)


# ============================================================
# JWT 工具函数
# ============================================================

def create_jwt(user_id, **extra):
    """
    生成 JWT Token
    :param user_id: 用户ID (openid)
    :param extra: 额外负载数据
    :return: JWT 字符串
    """
    try:
        import jwt as pyjwt
    except ImportError:
        logger.error("PyJWT 库未安装，请执行: pip install PyJWT")
        raise
    
    payload = {
        'user_id': user_id,
        'iat': int(time.time()),
        'exp': int(time.time()) + settings.JWT_EXPIRE_HOURS * 3600,
        'type': 'access',
        **extra
    }
    token = pyjwt.encode(payload, settings.JWT_SECRET, algorithm='HS256')
    # PyJWT 2.x 返回 str，1.x 返回 bytes
    return token if isinstance(token, str) else token.decode('utf-8')


def create_refresh_token(user_id):
    """生成刷新 Token（有效期更长）"""
    try:
        import jwt as pyjwt
    except ImportError:
        logger.error("PyJWT 库未安装，请执行: pip install PyJWT")
        raise
    
    payload = {
        'user_id': user_id,
        'iat': int(time.time()),
        'exp': int(time.time()) + settings.JWT_EXPIRE_HOURS * 7200,  # 刷新token有效期更长
        'type': 'refresh',
    }
    token = pyjwt.encode(payload, settings.JWT_SECRET, algorithm='HS256')
    return token if isinstance(token, str) else token.decode('utf-8')


def verify_jwt(token):
    """
    验证 JWT Token
    :param token: JWT 字符串
    :return: payload 字典 或 None
    """
    try:
        import jwt as pyjwt
    except ImportError:
        logger.error("PyJWT 库未安装，请执行: pip install PyJWT")
        return None
    
    if not token:
        return None
    
    # 去除 "Bearer " 前缀
    if token.startswith('Bearer '):
        token = token[7:]
    
    try:
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        # 检查 token 类型
        if payload.get('type') != 'access':
            logger.warning(f"JWT 类型错误: {payload.get('type')}")
            return None
        return payload
    except pyjwt.ExpiredSignatureError:
        logger.warning("JWT Token 已过期")
        return None
    except pyjwt.InvalidTokenError as e:
        logger.warning(f"JWT Token 无效: {e}")
        return None
    except Exception as e:
        logger.error(f"JWT 验证异常: {e}")
        return None


def verify_refresh_token(token):
    """验证刷新 Token"""
    try:
        import jwt as pyjwt
    except ImportError:
        return None
    
    if not token:
        return None
    
    if token.startswith('Bearer '):
        token = token[7:]
    
    try:
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        if payload.get('type') != 'refresh':
            return None
        return payload
    except pyjwt.ExpiredSignatureError:
        return None
    except pyjwt.InvalidTokenError:
        return None
    except Exception:
        return None


# ============================================================
# 文件/图片工具函数
# ============================================================

def get_file_hash(data):
    """
    计算文件内容的 MD5 哈希
    :param data: bytes 或文件对象
    :return: 32位小写 MD5 字符串
    """
    if hasattr(data, 'read'):
        md5 = hashlib.md5()
        for chunk in iter(lambda: data.read(8192), b''):
            md5.update(chunk)
        data.seek(0)
        return md5.hexdigest()
    return hashlib.md5(data).hexdigest()


def generate_file_id(file_hash, ext='jpg'):
    """
    生成唯一文件ID
    :param file_hash: 文件哈希
    :param ext: 文件扩展名
    :return: file_id 字符串
    """
    timestamp = int(time.time())
    random_str = uuid.uuid4().hex[:8]
    return f"{file_hash}_{timestamp}_{random_str}.{ext}"


def image_to_base64(data):
    """
    图片二进制数据转 Base64 字符串
    :param data: bytes
    :return: base64 字符串
    """
    return base64.b64encode(data).decode('utf-8')


def base64_to_image(b64_str):
    """
    Base64 字符串转图片二进制数据
    :param b64_str: base64 字符串
    :return: bytes
    """
    # 去除可能的 data:image/xxx;base64, 前缀
    if ',' in b64_str:
        b64_str = b64_str.split(',', 1)[1]
    return base64.b64decode(b64_str)


def get_file_extension(filename):
    """
    从文件名获取安全的扩展名
    :param filename: 原始文件名
    :return: 小写扩展名 (不含点)
    """
    ext = Path(filename).suffix.lower().lstrip('.')
    allowed = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'}
    return ext if ext in allowed else 'jpg'


def ensure_dir(path):
    """
    确保目录存在
    :param path: Path 对象或字符串
    """
    if isinstance(path, str):
        path = Path(path)
    path.mkdir(parents=True, exist_ok=True)


# ============================================================
# 时间/日期工具函数
# ============================================================

def now():
    """当前时间"""
    return datetime.now()


def now_str():
    """当前时间字符串"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def today_str():
    """今天日期字符串"""
    return datetime.now().strftime('%Y-%m-%d')


def today():
    """今天日期"""
    return datetime.now().date()


def get_client_ip(request):
    """
    获取客户端真实 IP 地址
    :param request: Django HttpRequest
    :return: IP 字符串
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip[:50]


# ============================================================
# 微信 API 工具函数
# ============================================================

def call_wechat_jscode2session(appid, secret, js_code):
    """
    调用微信 jscode2session 接口
    :param appid: 小程序 appid
    :param secret: 小程序 secret
    :param js_code: 前端获取的 code
    :return: dict (openid, session_key, unionid) 或 None
    """
    import urllib.request
    import urllib.parse
    
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = urllib.parse.urlencode({
        'appid': appid,
        'secret': secret,
        'js_code': js_code,
        'grant_type': 'authorization_code'
    })
    full_url = f"{url}?{params}"
    
    try:
        with urllib.request.urlopen(full_url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except Exception as e:
        logger.error(f"微信登录请求失败: {e}")
        return None


# ============================================================
# 响应帮助函数
# ============================================================

def file_response(file_path, content_type=None, as_attachment=False, filename=None):
    """
    返回文件响应
    :param file_path: 文件绝对路径
    :param content_type: MIME 类型
    :param as_attachment: 是否作为附件下载
    :param filename: 下载文件名
    :return: FileResponse 或错误 json_response
    """
    path = Path(file_path)
    if not path.exists():
        return error_response("文件不存在", code=404, status=404)
    
    if content_type is None:
        ext = path.suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png', '.gif': 'image/gif',
            '.bmp': 'image/bmp', '.webp': 'image/webp',
        }
        content_type = mime_types.get(ext, 'application/octet-stream')
    
    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    if as_attachment:
        response['Content-Disposition'] = f'attachment; filename="{filename or path.name}"'
    return response


def image_base64_response(file_path):
    """
    读取图片并返回 Base64 编码的 JSON 响应
    :param file_path: 文件路径
    :return: json_response
    """
    path = Path(file_path)
    if not path.exists():
        return error_response("图片不存在", code=404, status=404)
    
    try:
        with open(path, 'rb') as f:
            data = f.read()
        ext = path.suffix.lower().lstrip('.')
        if ext == 'jpg':
            ext = 'jpeg'
        mime_type = f"image/{ext}"
        b64_data = image_to_base64(data)
        return success_response(data={
            "base64": f"data:{mime_type};base64,{b64_data}",
            "file_id": path.name,
            "size": len(data)
        })
    except Exception as e:
        logger.error(f"读取图片失败: {e}")
        return error_response("读取图片失败")


# ============================================================
# 安全的文件保存
# ============================================================

def sanitize_filename(filename):
    """
    净化文件名，移除危险字符
    :param filename: 原始文件名
    :return: 安全文件名
    """
    # 只保留字母数字、点、下划线和连字符
    sanitized = re.sub(r'[^\w\.\-_]', '', filename)
    # 限制长度
    return sanitized[:255] if sanitized else 'unnamed'


def save_uploaded_file(file_obj, save_dir, filename=None):
    """
    安全保存上传的文件
    :param file_obj: Django UploadedFile 对象
    :param save_dir: 保存目录 (Path 对象)
    :param filename: 可选的自定义文件名
    :return: 保存后的文件名
    """
    ensure_dir(save_dir)
    
    if filename is None:
        ext = get_file_extension(file_obj.name)
        file_id = generate_file_id(get_file_hash(file_obj), ext)
    else:
        file_id = sanitize_filename(filename)
    
    save_path = save_dir / file_id
    
    with open(save_path, 'wb') as f:
        for chunk in file_obj.chunks():
            f.write(chunk)
    
    return file_id
