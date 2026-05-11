"""
拾光旧影 - AI老照片修复后端服务 v2.0
整合: 微信登录 + JWT认证 + 数据统计 + 管理后台
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

from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 已有模块
from api_manager import APIRouter, RepairMode, get_router

# 新增模块
from config import Config
from models import user_dao, record_dao, stats_dao
from auth import auth_bp, login_required
from stats import stats_bp, track_repair
from admin_routes import register_admin

# ============ 初始化应用 ============
app = Flask(__name__, template_folder='templates')
app.secret_key = Config.JWT_SECRET
CORS(app)

# 上传配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
RESULT_FOLDER = os.path.join(os.path.dirname(__file__), 'results')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'webp'}
MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 注册蓝图
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(stats_bp, url_prefix='/api/stats')
register_admin(app)

# 用户/历史JSON文件（兼容v1）
USER_DB_FILE = os.path.join(os.path.dirname(__file__), 'users.json')
HISTORY_DB_FILE = os.path.join(os.path.dirname(__file__), 'history.json')

# ============ 工具函数 ============
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_hash(file_data: bytes) -> str:
    return hashlib.md5(file_data).hexdigest()

def image_to_base64(file_data: bytes) -> str:
    return base64.b64encode(file_data).decode('utf-8')

def save_result_image(image_data: bytes, file_id: str) -> str:
    filepath = os.path.join(RESULT_FOLDER, f"{file_id}.jpg")
    with open(filepath, 'wb') as f:
        f.write(image_data)
    return filepath

def check_cache(file_hash: str, mode: str) -> str:
    cache_file = os.path.join(RESULT_FOLDER, f"cache_{file_hash}_{mode}.jpg")
    return cache_file if os.path.exists(cache_file) else None

def save_cache(file_hash: str, mode: str, image_data: bytes) -> str:
    cache_file = os.path.join(RESULT_FOLDER, f"cache_{file_hash}_{mode}.jpg")
    with open(cache_file, 'wb') as f:
        f.write(image_data)
    return cache_file

def success_response(data=None, message="操作成功"):
    return jsonify({"code": 0, "message": message, "data": data or {}, "timestamp": int(time.time())})

def error_response(code=500, message="操作失败", data=None):
    return jsonify({"code": code, "message": message, "data": data or {}, "timestamp": int(time.time())}), code

# ============ 兼容v1的用户管理 ============

def load_json(filepath: str, default=None):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default or {}

def save_json(filepath: str, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_or_create_user(openid: str) -> dict:
    """v1兼容 - 同时同步到v2模型"""
    user = user_dao.get_by_id(openid)
    if not user:
        user = user_dao.create_user(openid=openid)
    return user.to_dict()

def update_user(openid: str, updates: dict):
    user = user_dao.get_by_id(openid)
    if user:
        for k, v in updates.items():
            setattr(user, k, v)
        user_dao.save(user)

def add_history(openid: str, record: dict):
    history = load_json(HISTORY_DB_FILE, {})
    if openid not in history:
        history[openid] = []
    history[openid].insert(0, record)
    history[openid] = history[openid][:50]
    save_json(HISTORY_DB_FILE, history)

def get_user_history(openid: str) -> list:
    history = load_json(HISTORY_DB_FILE, {})
    return history.get(openid, [])

def can_user_repair(openid: str) -> tuple:
    user = user_dao.get_by_id(openid)
    if not user:
        user = user_dao.create_user(openid=openid)
    
    if user.is_member and user.member_expire and user.member_expire > datetime.now().isoformat():
        return True, "会员无限次"
    if user.free_remaining > 0:
        return True, f"免费剩余{user.free_remaining}次"
    return False, "免费次数已用完，请开通会员"

# ============ API路由 ============

@app.route("/")
def index():
    return jsonify({
        "name": "拾光旧影 - AI老照片修复API v2.0",
        "version": "2.0.0",
        "status": "running",
        "features": ["微信登录", "JWT认证", "数据统计", "管理后台"],
        "endpoints": {
            "auth": "/api/auth/* - 登录认证",
            "upload": "POST /api/upload - 上传图片",
            "repair": "POST /api/repair - 修复图片",
            "result": "GET /api/result/<file_id> - 获取结果",
            "history": "GET /api/history - 修复历史",
            "stats": "/api/stats/* - 数据统计",
            "admin": "/admin/ - 管理后台"
        }
    })


@app.route("/api/upload", methods=["POST"])
def upload_image():
    """上传图片"""
    try:
        if 'image' in request.files:
            file = request.files['image']
            if file.filename == '':
                return error_response(400, "未选择文件")
            if not allowed_file(file.filename):
                return error_response(400, "不支持的文件类型")
            file_data = file.read()
        elif request.json and 'image' in request.json:
            b64_data = request.json['image']
            if ',' in b64_data:
                b64_data = b64_data.split(',')[1]
            file_data = base64.b64decode(b64_data)
        else:
            return error_response(400, "请上传图片或提供base64数据")
        
        if len(file_data) > MAX_CONTENT_LENGTH:
            return error_response(400, "图片超过20MB")
        
        file_hash = get_file_hash(file_data)
        file_id = f"{file_hash}_{uuid.uuid4().hex[:8]}"
        
        with open(os.path.join(UPLOAD_FOLDER, f"{file_id}.jpg"), 'wb') as f:
            f.write(file_data)
        
        return success_response({
            "file_id": file_id,
            "file_hash": file_hash,
            "size": len(file_data),
            "url": f"/api/image/{file_id}"
        })
    except Exception as e:
        return error_response(500, f"上传失败: {str(e)}")


@app.route("/api/repair", methods=["POST"])
@login_required
def repair_image():
    """修复图片 - 核心接口（需登录）"""
    try:
        data = request.get_json() or {}
        file_id = data.get("file_id", "")
        mode_str = data.get("mode", "enhance")
        # 从JWT获取用户ID
        user_id = getattr(request, 'user_id', 'guest')
        
        if not file_id:
            return error_response(400, "缺少file_id")
        
        try:
            mode = RepairMode(mode_str)
        except ValueError:
            return error_response(400, f"不支持的模式: {mode_str}")
        
        # 检查权限
        can_repair, reason = can_user_repair(user_id)
        if not can_repair:
            return error_response(403, reason)
        
        # 读取图片
        upload_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.jpg")
        if not os.path.exists(upload_path):
            return error_response(404, "图片不存在")
        
        with open(upload_path, 'rb') as f:
            file_data = f.read()
        file_hash = get_file_hash(file_data)
        
        # 缓存检查
        cache_path = check_cache(file_hash, mode.value)
        if cache_path:
            return success_response({
                "file_id": f"cache_{file_hash}_{mode.value}",
                "mode": mode.value, "cached": True,
                "url": f"/api/result/cache_{file_hash}_{mode.value}"
            })
        
        # AI修复
        image_b64 = image_to_base64(file_data)
        router = get_router()
        result = router.repair(image_b64, mode)
        
        if not result.success:
            # 记录错误
            track_repair(user_id, mode.value, "error", 0, False)
            return error_response(500, f"修复失败: {result.message}")
        
        # 保存结果
        result_id = f"result_{uuid.uuid4().hex[:12]}"
        save_result_image(result.image_data, result_id)
        save_cache(file_hash, mode.value, result.image_data)
        
        # 扣除次数
        user = user_dao.get_by_id(user_id)
        if user and not user.is_member and user.free_remaining > 0:
            user.free_remaining -= 1
            user.total_repairs += 1
            user_dao.save(user)
        elif user:
            user.total_repairs += 1
            user_dao.save(user)
        
        # 记录修复（数据统计）
        track_repair(user_id, mode.value, result.platform, result.cost_time, True)
        
        # 保存修复记录
        record_dao.create(user_id=user_id, mode=mode.value, 
                         platform=result.platform, cost_time=result.cost_time)
        
        # v1兼容历史
        history_record = {
            "id": result_id, "file_id": file_id, "mode": mode.value,
            "mode_name": {"colorize": "黑白上色", "repair": "破损修复",
                         "enhance": "清晰度增强", "denoise": "智能去噪"}.get(mode.value),
            "platform": result.platform, "cost_time": round(result.cost_time, 2),
            "created_at": datetime.now().isoformat(),
            "result_url": f"/api/result/{result_id}"
        }
        add_history(user_id, history_record)
        
        remaining = user.free_remaining if user and not user.is_member else -1
        return success_response({
            "file_id": result_id, "mode": mode.value, "cached": False,
            "url": f"/api/result/{result_id}",
            "preview_url": f"/api/result/{result_id}?base64=1",
            "cost_time": round(result.cost_time, 2),
            "platform": result.platform,
            "remaining": remaining
        }, "修复成功")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(500, f"修复失败: {str(e)}")


@app.route("/api/result/<file_id>", methods=["GET"])
def get_result(file_id: str):
    """获取修复结果"""
    try:
        filepath = os.path.join(RESULT_FOLDER, f"{file_id}.jpg")
        if not os.path.exists(filepath):
            return error_response(404, "结果不存在")
        
        if request.args.get("base64") == "1":
            with open(filepath, 'rb') as f:
                b64_data = base64.b64encode(f.read()).decode()
            return success_response({"image_base64": f"data:image/jpeg;base64,{b64_data}"})
        
        return send_file(filepath, mimetype='image/jpeg')
    except Exception as e:
        return error_response(500, f"获取失败: {str(e)}")


@app.route("/api/image/<file_id>", methods=["GET"])
def get_uploaded_image(file_id: str):
    filepath = os.path.join(UPLOAD_FOLDER, f"{file_id}.jpg")
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    return error_response(404, "图片不存在")


@app.route("/api/history", methods=["GET"])
@login_required
def get_history():
    """获取修复历史"""
    user_id = getattr(request, 'user_id', 'guest')
    history = get_user_history(user_id)
    return success_response({"total": len(history), "list": history})


@app.route("/api/history/<history_id>", methods=["DELETE"])
@login_required
def delete_history(history_id: str):
    """删除历史"""
    user_id = getattr(request, 'user_id', 'guest')
    history = load_json(HISTORY_DB_FILE, {})
    if user_id in history:
        history[user_id] = [h for h in history[user_id] if h["id"] != history_id]
        save_json(HISTORY_DB_FILE, history)
    return success_response(message="删除成功")


@app.route("/api/user", methods=["GET"])
@login_required
def get_user():
    """获取当前用户信息"""
    user_id = getattr(request, 'user_id', 'guest')
    user = user_dao.get_by_id(user_id)
    if user:
        return success_response(user.to_dict())
    return error_response(404, "用户不存在")


@app.route("/api/quota", methods=["GET"])
def get_quota():
    """获取API配额"""
    try:
        router = get_router()
        quotas = router.get_quota_status()
        return success_response({
            "quotas": quotas,
            "total_remaining": sum(q["remaining"] for q in quotas)
        })
    except Exception as e:
        return error_response(500, f"获取配额失败: {str(e)}")


@app.route("/health")
def health_check():
    router = get_router()
    quotas = router.get_quota_status()
    total_remaining = sum(q["remaining"] for q in quotas)
    return jsonify({
        "status": "healthy" if total_remaining > 0 else "quota_exhausted",
        "version": "2.0.0",
        "time": datetime.now().isoformat(),
        "total_remaining_quota": total_remaining,
        "platforms_active": len(router.platforms),
        "features": ["微信登录", "JWT认证", "数据统计", "管理后台"]
    })


# ============ 错误处理 ============
@app.errorhandler(413)
def too_large(e): return error_response(413, "文件大小超过20MB")
@app.errorhandler(404)
def not_found(e): return error_response(404, "接口不存在")
@app.errorhandler(500)
def server_error(e): return error_response(500, "服务器内部错误")

# ============ 启动 ============
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    print("=" * 50)
    print("  拾光旧影 v2.0 - AI老照片修复后端服务")
    print("  新增: 微信登录 + JWT认证 + 数据统计 + 管理后台")
    print("=" * 50)
    print(f"  服务地址: http://0.0.0.0:{port}")
    print(f"  管理后台: http://0.0.0.0:{port}/admin/")
    print(f"  调试模式: {debug}")
    print("=" * 50)
    
    app.run(host="0.0.0.0", port=port, debug=debug)
