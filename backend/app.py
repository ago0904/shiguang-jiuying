"""
拾光旧影 - AI老照片修复后端服务
Flask + 多平台API轮询
"""
import os
import sys
import base64
import json
import uuid
import hashlib
import time
from datetime import datetime
from io import BytesIO
from functools import wraps

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

from api_manager import APIRouter, RepairMode, get_router

# ============ 配置 ============
app = Flask(__name__)
CORS(app)  # 允许跨域，微信小程序需要

# 上传配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
RESULT_FOLDER = os.path.join(os.path.dirname(__file__), 'results')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'webp'}
MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 模拟用户数据库（生产环境应使用真实数据库）
USER_DB_FILE = os.path.join(os.path.dirname(__file__), 'users.json')

# 修复历史记录
HISTORY_DB_FILE = os.path.join(os.path.dirname(__file__), 'history.json')


def load_json(filepath: str, default=None):
    """加载JSON文件"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default or {}


def save_json(filepath: str, data):
    """保存JSON文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============ 工具函数 ============

def allowed_file(filename: str) -> bool:
    """检查文件类型"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_hash(file_data: bytes) -> str:
    """计算文件哈希（用于缓存）"""
    return hashlib.md5(file_data).hexdigest()


def image_to_base64(file_data: bytes) -> str:
    """图片转base64"""
    return base64.b64encode(file_data).decode('utf-8')


def base64_to_image(b64_string: str) -> bytes:
    """base64转图片"""
    return base64.b64decode(b64_string)


def save_result_image(image_data: bytes, file_id: str) -> str:
    """保存修复后的图片"""
    filepath = os.path.join(RESULT_FOLDER, f"{file_id}.jpg")
    with open(filepath, 'wb') as f:
        f.write(image_data)
    return filepath


def check_cache(file_hash: str, mode: str) -> str:
    """检查是否有缓存结果"""
    cache_key = f"{file_hash}_{mode}"
    cache_file = os.path.join(RESULT_FOLDER, f"cache_{cache_key}.jpg")
    if os.path.exists(cache_file):
        return cache_file
    return None


def save_cache(file_hash: str, mode: str, image_data: bytes) -> str:
    """保存缓存结果"""
    cache_key = f"{file_hash}_{mode}"
    cache_file = os.path.join(RESULT_FOLDER, f"cache_{cache_key}.jpg")
    with open(cache_file, 'wb') as f:
        f.write(image_data)
    return cache_file


# ============ 统一响应格式 ============

def success_response(data=None, message="操作成功"):
    """成功响应"""
    return jsonify({
        "code": 0,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time())
    })


def error_response(code=500, message="操作失败", data=None):
    """错误响应"""
    return jsonify({
        "code": code,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time())
    }), code


# ============ 用户管理 ============

def get_or_create_user(openid: str) -> dict:
    """获取或创建用户"""
    users = load_json(USER_DB_FILE, {})
    if openid not in users:
        users[openid] = {
            "openid": openid,
            "created_at": datetime.now().isoformat(),
            "total_repairs": 0,
            "free_remaining": 3,  # 新用户免费3次
            "is_member": False,
            "member_expire": "",
            "history_ids": []
        }
        save_json(USER_DB_FILE, users)
    return users[openid]


def update_user(openid: str, updates: dict):
    """更新用户信息"""
    users = load_json(USER_DB_FILE, {})
    if openid in users:
        users[openid].update(updates)
        save_json(USER_DB_FILE, users)


def add_history(openid: str, record: dict):
    """添加修复历史"""
    history = load_json(HISTORY_DB_FILE, {})
    if openid not in history:
        history[openid] = []
    history[openid].insert(0, record)
    # 只保留最近50条
    history[openid] = history[openid][:50]
    save_json(HISTORY_DB_FILE, history)
    
    # 更新用户的history_ids
    users = load_json(USER_DB_FILE, {})
    if openid in users:
        users[openid]["history_ids"] = [h["id"] for h in history[openid]]
        save_json(USER_DB_FILE, users)


def get_user_history(openid: str) -> list:
    """获取用户历史"""
    history = load_json(HISTORY_DB_FILE, {})
    return history.get(openid, [])


def can_user_repair(openid: str) -> tuple:
    """检查用户是否可以修复"""
    user = get_or_create_user(openid)
    
    # 会员可以无限修复
    if user.get("is_member"):
        expire = user.get("member_expire", "")
        if expire and expire > datetime.now().isoformat():
            return True, "会员无限次"
    
    # 免费次数
    free = user.get("free_remaining", 0)
    if free > 0:
        return True, f"免费剩余{free}次"
    
    return False, "免费次数已用完，请开通会员"


# ============ API路由 ============

@app.route("/")
def index():
    """首页"""
    return jsonify({
        "name": "拾光旧影 - AI老照片修复API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "quota": "GET /api/quota - 查看API配额",
            "upload": "POST /api/upload - 上传图片",
            "repair": "POST /api/repair - 修复图片",
            "result": "GET /api/result/<file_id> - 获取结果图片",
            "history": "GET /api/history - 获取修复历史",
            "user": "GET /api/user - 获取用户信息"
        }
    })


@app.route("/api/quota", methods=["GET"])
def get_quota():
    """获取所有API平台的配额状态"""
    try:
        router = get_router()
        quotas = router.get_quota_status()
        return success_response({
            "quotas": quotas,
            "total_free_monthly": sum(q["free_limit"] for q in quotas),
            "total_used": sum(q["used"] for q in quotas),
            "total_remaining": sum(q["remaining"] for q in quotas)
        })
    except Exception as e:
        return error_response(500, f"获取配额失败: {str(e)}")


@app.route("/api/user", methods=["GET"])
def get_user():
    """获取用户信息"""
    openid = request.args.get("openid", "")
    if not openid:
        # 游客模式
        return success_response({
            "is_guest": True,
            "free_remaining": 1,
            "message": "游客模式，可体验1次"
        })
    
    user = get_or_create_user(openid)
    return success_response(user)


@app.route("/api/upload", methods=["POST"])
def upload_image():
    """上传图片接口"""
    try:
        # 检查是否有文件
        if 'image' in request.files:
            file = request.files['image']
            if file.filename == '':
                return error_response(400, "未选择文件")
            if not allowed_file(file.filename):
                return error_response(400, "不支持的文件类型，请上传JPG/PNG/BMP")
            
            file_data = file.read()
        elif request.json and 'image' in request.json:
            # base64编码的图片
            b64_data = request.json['image']
            if ',' in b64_data:
                b64_data = b64_data.split(',')[1]
            file_data = base64.b64decode(b64_data)
        else:
            return error_response(400, "请上传图片文件或提供base64图片数据")
        
        # 检查文件大小
        if len(file_data) > MAX_CONTENT_LENGTH:
            return error_response(400, "图片大小超过20MB限制")
        
        # 生成文件ID
        file_hash = get_file_hash(file_data)
        file_id = f"{file_hash}_{uuid.uuid4().hex[:8]}"
        
        # 保存上传的图片
        upload_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.jpg")
        with open(upload_path, 'wb') as f:
            f.write(file_data)
        
        return success_response({
            "file_id": file_id,
            "file_hash": file_hash,
            "size": len(file_data),
            "url": f"/api/image/{file_id}"
        }, "上传成功")
        
    except Exception as e:
        return error_response(500, f"上传失败: {str(e)}")


@app.route("/api/repair", methods=["POST"])
def repair_image():
    """
    修复图片 - 核心接口
    
    请求参数:
    {
        "file_id": "xxx",           // 上传后返回的文件ID
        "mode": "colorize",         // 修复模式: colorize/repair/enhance/denoise
        "openid": "xxx"             // 用户openid（可选，不传则为游客）
    }
    """
    try:
        data = request.get_json() or {}
        file_id = data.get("file_id", "")
        mode_str = data.get("mode", "enhance")
        openid = data.get("openid", "guest")
        
        # 验证参数
        if not file_id:
            return error_response(400, "缺少file_id参数")
        
        try:
            mode = RepairMode(mode_str)
        except ValueError:
            return error_response(400, f"不支持的修复模式: {mode_str}")
        
        # 检查用户权限
        can_repair, reason = can_user_repair(openid)
        if not can_repair:
            return error_response(403, reason)
        
        # 读取上传的图片
        upload_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.jpg")
        if not os.path.exists(upload_path):
            return error_response(404, "图片不存在，请重新上传")
        
        with open(upload_path, 'rb') as f:
            file_data = f.read()
        
        file_hash = get_file_hash(file_data)
        
        # 检查缓存
        cache_path = check_cache(file_hash, mode.value)
        if cache_path:
            # 返回缓存结果
            result_id = f"cache_{file_hash}_{mode.value}"
            return success_response({
                "file_id": result_id,
                "mode": mode.value,
                "cached": True,
                "url": f"/api/result/{result_id}",
                "cost_time": 0,
                "platform": "cache",
                "remaining_quota": reason
            }, "返回缓存结果")
        
        # 转换为base64
        image_b64 = image_to_base64(file_data)
        
        # 调用API修复
        router = get_router()
        result = router.repair(image_b64, mode)
        
        if not result.success:
            return error_response(500, f"修复失败: {result.message}")
        
        # 保存结果
        result_id = f"result_{uuid.uuid4().hex[:12]}"
        result_path = save_result_image(result.image_data, result_id)
        
        # 保存缓存
        save_cache(file_hash, mode.value, result.image_data)
        
        # 扣除用户免费次数
        user = get_or_create_user(openid)
        if not user.get("is_member") and user.get("free_remaining", 0) > 0:
            user["free_remaining"] -= 1
            user["total_repairs"] += 1
            update_user(openid, user)
        
        # 添加历史记录
        history_record = {
            "id": result_id,
            "file_id": file_id,
            "mode": mode.value,
            "mode_name": {
                "colorize": "黑白上色",
                "repair": "破损修复",
                "enhance": "清晰度增强",
                "denoise": "智能去噪"
            }.get(mode.value, mode.value),
            "platform": result.platform,
            "cost_time": round(result.cost_time, 2),
            "created_at": datetime.now().isoformat(),
            "result_url": f"/api/result/{result_id}"
        }
        add_history(openid, history_record)
        
        return success_response({
            "file_id": result_id,
            "mode": mode.value,
            "cached": False,
            "url": f"/api/result/{result_id}",
            "preview_url": f"/api/result/{result_id}?base64=1",
            "cost_time": round(result.cost_time, 2),
            "platform": result.platform,
            "remaining_quota": f"免费剩余{user.get('free_remaining', 0)}次" if not user.get("is_member") else "会员无限"
        }, "修复成功")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(500, f"修复失败: {str(e)}")


@app.route("/api/result/<file_id>", methods=["GET"])
def get_result(file_id: str):
    """获取修复结果图片"""
    try:
        # 检查是否是缓存结果
        if file_id.startswith("cache_"):
            filepath = os.path.join(RESULT_FOLDER, f"{file_id}.jpg")
        else:
            filepath = os.path.join(RESULT_FOLDER, f"{file_id}.jpg")
        
        if not os.path.exists(filepath):
            return error_response(404, "结果图片不存在")
        
        # 返回base64
        if request.args.get("base64") == "1":
            with open(filepath, 'rb') as f:
                b64_data = base64.b64encode(f.read()).decode('utf-8')
            return success_response({
                "image_base64": f"data:image/jpeg;base64,{b64_data}"
            })
        
        # 返回图片文件
        return send_file(filepath, mimetype='image/jpeg')
        
    except Exception as e:
        return error_response(500, f"获取结果失败: {str(e)}")


@app.route("/api/image/<file_id>", methods=["GET"])
def get_uploaded_image(file_id: str):
    """获取上传的原图"""
    filepath = os.path.join(UPLOAD_FOLDER, f"{file_id}.jpg")
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    return error_response(404, "图片不存在")


@app.route("/api/history", methods=["GET"])
def get_history():
    """获取修复历史"""
    openid = request.args.get("openid", "guest")
    history = get_user_history(openid)
    return success_response({
        "total": len(history),
        "list": history
    })


@app.route("/api/history/<history_id>", methods=["DELETE"])
def delete_history(history_id: str):
    """删除历史记录"""
    openid = request.args.get("openid", "guest")
    history = load_json(HISTORY_DB_FILE, {})
    if openid in history:
        history[openid] = [h for h in history[openid] if h["id"] != history_id]
        save_json(HISTORY_DB_FILE, history)
    return success_response(message="删除成功")


# ============ 健康检查 ============

@app.route("/health")
def health_check():
    """健康检查"""
    router = get_router()
    quotas = router.get_quota_status()
    total_remaining = sum(q["remaining"] for q in quotas)
    
    return jsonify({
        "status": "healthy" if total_remaining > 0 else "quota_exhausted",
        "time": datetime.now().isoformat(),
        "total_remaining_quota": total_remaining,
        "platforms_active": len(router.platforms)
    })


# ============ 错误处理 ============

@app.errorhandler(413)
def too_large(e):
    return error_response(413, "文件大小超过20MB限制")


@app.errorhandler(404)
def not_found(e):
    return error_response(404, "接口不存在")


@app.errorhandler(500)
def server_error(e):
    return error_response(500, "服务器内部错误")


# ============ 启动 ============

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    print("=" * 50)
    print("  拾光旧影 - AI老照片修复后端服务")
    print("=" * 50)
    print(f"  服务地址: http://0.0.0.0:{port}")
    print(f"  调试模式: {debug}")
    print("=" * 50)
    
    # 打印配额状态
    router = get_router()
    quotas = router.get_quota_status()
    print("\n📊 API配额状态:")
    for q in quotas:
        status = "✅" if q["remaining"] > 0 else "❌"
        print(f"  {status} {q['platform']} - {q['mode']}: {q['used']}/{q['free_limit']} (剩余{q['remaining']})")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
