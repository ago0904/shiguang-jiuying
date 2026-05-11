"""
管理后台API - 需要管理员权限
拾光旧影 - 管理后台接口模块
提供完整的后台管理功能：认证、数据看板、用户管理、修复记录、系统设置、配额管理
"""

import time
import uuid
import random
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, current_app

# ============================================================
# 蓝图定义
# ============================================================

admin_api_bp = Blueprint('admin_api', __name__)

# ============================================================
# 模拟数据存储（生产环境应替换为数据库操作）
# ============================================================

# 管理员账号存储
ADMIN_ACCOUNTS = {
    "admin": {
        "password": "admin123",  # 生产环境应使用哈希存储
        "role": "super_admin",
        "name": "超级管理员"
    }
}

# Token存储 {token: {username, expire_time}}
ADMIN_TOKENS = {}

# 模拟用户数据
MOCK_USERS = []
for i in range(1, 101):
    MOCK_USERS.append({
        "id": f"U{10000 + i}",
        "nickname": random.choice(["小明", "小红", "老王", "张三", "李四", "王五", "赵六", "孙七", "周八", "吴九",
                                   "咖啡猫", "阳光少年", "月光女神", "风之子", "海洋之心", "星空漫步", "旅行者", "摄影师",
                                   "怀旧达人", "影像修复师", "老照片收藏家", "时光旅人", "记忆守护者", "复古控"]) + f"_{i}",
        "avatar": f"https://api.dicebear.com/7.x/avataaars/svg?seed=user{i}",
        "platform": random.choice(["wechat", "alipay", "douyin", "qq"]),
        "open_id": f"openid_{uuid.uuid4().hex[:16]}",
        "status": random.choice(["active", "active", "active", "active", "banned"]),
        "is_member": random.choice([True, False, False, False]),
        "member_expire": (datetime.now() + timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d") if random.random() > 0.7 else None,
        "repair_count": random.randint(0, 200),
        "free_used": random.randint(0, 10),
        "created_at": (datetime.now() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d %H:%M:%S"),
        "last_login": (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d %H:%M:%S"),
        "ip": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    })

# 模拟修复记录
MOCK_RECORDS = []
MODES = ["colorize", "repair", "enhance", "denoise"]
MODE_NAMES = {"colorize": "上色", "repair": "修复", "enhance": "增强", "denoise": "去噪"}
PLATFORMS = ["wechat", "alipay", "douyin", "qq"]
for i in range(1, 201):
    mode = random.choice(MODES)
    MOCK_RECORDS.append({
        "id": f"R{100000 + i}",
        "user_id": random.choice(MOCK_USERS)["id"],
        "user_nickname": random.choice(MOCK_USERS)["nickname"],
        "mode": mode,
        "mode_name": MODE_NAMES[mode],
        "platform": random.choice(PLATFORMS),
        "status": random.choice(["success", "success", "success", "success", "failed", "processing"]),
        "cost": round(random.uniform(0.5, 5.0), 1),
        "created_at": (datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))).strftime("%Y-%m-%d %H:%M:%S"),
        "duration": random.randint(1, 30),
        "image_url": f"/api/images/sample_{i % 20 + 1}.jpg"
    })

# 模拟系统设置
SYSTEM_SETTINGS = {
    "free_daily_limit": 3,
    "member_price_monthly": 19.9,
    "member_price_quarterly": 49.9,
    "member_price_yearly": 169.9,
    "member_daily_limit": 50,
    "wechat_enabled": True,
    "alipay_enabled": True,
    "douyin_enabled": True,
    "qq_enabled": True,
    "colorize_enabled": True,
    "repair_enabled": True,
    "enhance_enabled": True,
    "denoise_enabled": True,
    "max_image_size": 10,
    "support_email": "support@shiguangjiuying.com",
    "system_notice": ""
}

# 模拟平台配额
PLATFORM_QUOTA = {
    "wechat": {"name": "微信", "quota": 5000, "used": 3456, "remaining": 1544, "status": "normal", "expire": "2026-12-31"},
    "alipay": {"name": "支付宝", "quota": 5000, "used": 2890, "remaining": 2110, "status": "normal", "expire": "2026-12-31"},
    "douyin": {"name": "抖音", "quota": 3000, "used": 2100, "remaining": 900, "status": "warning", "expire": "2026-06-30"},
    "qq": {"name": "QQ", "quota": 3000, "used": 1500, "remaining": 1500, "status": "normal", "expire": "2026-12-31"},
}

# ============================================================
# 工具函数
# ============================================================

def api_response(code=0, message="success", data=None):
    """统一API返回格式"""
    return jsonify({
        "code": code,
        "message": message,
        "data": data,
        "timestamp": int(time.time())
    })


def require_admin(f):
    """管理员权限校验装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-Admin-Token', '')
        if not token:
            return api_response(code=401, message="未登录，请先登录")
        if token not in ADMIN_TOKENS:
            return api_response(code=401, message="登录已过期，请重新登录")
        token_info = ADMIN_TOKENS[token]
        if token_info['expire_time'] < time.time():
            del ADMIN_TOKENS[token]
            return api_response(code=401, message="登录已过期，请重新登录")
        # 刷新过期时间（每次请求延长2小时）
        token_info['expire_time'] = time.time() + 7200
        request.admin_user = token_info['username']
        return f(*args, **kwargs)
    return decorated


def generate_dashboard_data():
    """生成看板数据"""
    # 近7天趋势数据
    trend_7d = []
    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%m-%d")
        trend_7d.append({
            "date": date,
            "repairs": random.randint(100, 200),
            "users": random.randint(50, 120),
            "revenue": round(random.uniform(50, 150), 1)
        })

    # 今日24小时数据
    hourly_today = [random.randint(1, 20) for _ in range(24)]

    # 修复模式分布
    mode_distribution = {
        "colorize": sum(1 for r in MOCK_RECORDS if r['mode'] == 'colorize'),
        "repair": sum(1 for r in MOCK_RECORDS if r['mode'] == 'repair'),
        "enhance": sum(1 for r in MOCK_RECORDS if r['mode'] == 'enhance'),
        "denoise": sum(1 for r in MOCK_RECORDS if r['mode'] == 'denoise'),
    }

    # 统计数据
    total_users = len(MOCK_USERS)
    total_repairs = len(MOCK_RECORDS)
    member_users = sum(1 for u in MOCK_USERS if u['is_member'])

    return {
        "today_repairs": random.randint(100, 200),
        "today_users": random.randint(50, 120),
        "today_new_users": random.randint(10, 40),
        "total_users": total_users,
        "total_repairs": total_repairs,
        "member_users": member_users,
        "revenue_today": round(random.uniform(50, 150), 1),
        "revenue_month": round(random.uniform(1500, 3000), 1),
        "trend_7d": trend_7d,
        "mode_distribution": mode_distribution,
        "hourly_today": hourly_today
    }


# ============================================================
# 认证路由
# ============================================================

@admin_api_bp.route('/login', methods=['POST'])
def admin_login():
    """管理员登录"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return api_response(code=400, message="用户名和密码不能为空")

    admin = ADMIN_ACCOUNTS.get(username)
    if not admin or admin['password'] != password:
        return api_response(code=401, message="用户名或密码错误")

    # 生成Token
    token = uuid.uuid4().hex
    ADMIN_TOKENS[token] = {
        "username": username,
        "role": admin['role'],
        "expire_time": time.time() + 7200  # 2小时有效期
    }

    return api_response(data={
        "token": token,
        "username": username,
        "role": admin['role'],
        "name": admin['name'],
        "expire_in": 7200
    })


@admin_api_bp.route('/check', methods=['GET'])
@require_admin
def admin_check():
    """检查登录状态"""
    token = request.headers.get('X-Admin-Token', '')
    token_info = ADMIN_TOKENS[token]
    admin = ADMIN_ACCOUNTS[token_info['username']]
    return api_response(data={
        "username": token_info['username'],
        "role": token_info['role'],
        "name": admin['name'],
        "expire_in": int(token_info['expire_time'] - time.time())
    })


# ============================================================
# 数据看板路由
# ============================================================

@admin_api_bp.route('/dashboard', methods=['GET'])
@require_admin
def dashboard():
    """看板数据汇总"""
    data = generate_dashboard_data()

    # 最新修复记录
    latest_records = sorted(MOCK_RECORDS, key=lambda x: x['created_at'], reverse=True)[:10]

    # 最新注册用户
    latest_users = sorted(MOCK_USERS, key=lambda x: x['created_at'], reverse=True)[:10]

    data['latest_records'] = latest_records
    data['latest_users'] = latest_users

    return api_response(data=data)


# ============================================================
# 用户管理路由
# ============================================================

@admin_api_bp.route('/users', methods=['GET'])
@require_admin
def user_list():
    """用户列表 - 支持分页和搜索"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    keyword = request.args.get('keyword', '').strip()
    status = request.args.get('status', '')
    platform = request.args.get('platform', '')

    users = MOCK_USERS.copy()

    # 搜索过滤
    if keyword:
        users = [u for u in users if keyword.lower() in u['nickname'].lower()
                 or keyword.lower() in u['id'].lower()]

    # 状态过滤
    if status:
        users = [u for u in users if u['status'] == status]

    # 平台过滤
    if platform:
        users = [u for u in users if u['platform'] == platform]

    total = len(users)
    start = (page - 1) * limit
    end = start + limit
    users_page = users[start:end]

    return api_response(data={
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "list": users_page
    })


@admin_api_bp.route('/users/<user_id>', methods=['GET'])
@require_admin
def user_detail(user_id):
    """用户详情"""
    user = next((u for u in MOCK_USERS if u['id'] == user_id), None)
    if not user:
        return api_response(code=404, message="用户不存在")
    return api_response(data=user)


@admin_api_bp.route('/users/<user_id>/status', methods=['POST'])
@require_admin
def user_status(user_id):
    """修改用户状态（启用/禁用）"""
    data = request.get_json() or {}
    status = data.get('status', '')

    if status not in ['active', 'banned']:
        return api_response(code=400, message="状态参数错误，应为 active 或 banned")

    user = next((u for u in MOCK_USERS if u['id'] == user_id), None)
    if not user:
        return api_response(code=404, message="用户不存在")

    user['status'] = status
    action = "启用" if status == 'active' else "禁用"
    return api_response(message=f"用户已{action}")


@admin_api_bp.route('/users/<user_id>/member', methods=['POST'])
@require_admin
def user_member(user_id):
    """设置会员状态"""
    data = request.get_json() or {}
    is_member = data.get('is_member', False)
    expire_days = data.get('expire_days', 30)

    user = next((u for u in MOCK_USERS if u['id'] == user_id), None)
    if not user:
        return api_response(code=404, message="用户不存在")

    user['is_member'] = is_member
    if is_member:
        user['member_expire'] = (datetime.now() + timedelta(days=expire_days)).strftime("%Y-%m-%d")
    else:
        user['member_expire'] = None

    action = "设为会员" if is_member else "取消会员"
    return api_response(message=f"已{action}")


@admin_api_bp.route('/users/<user_id>/history', methods=['GET'])
@require_admin
def user_history(user_id):
    """用户修复历史"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)

    records = [r for r in MOCK_RECORDS if r['user_id'] == user_id]
    records.sort(key=lambda x: x['created_at'], reverse=True)

    total = len(records)
    start = (page - 1) * limit
    end = start + limit

    return api_response(data={
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "list": records[start:end]
    })


# ============================================================
# 修复记录路由
# ============================================================

@admin_api_bp.route('/records', methods=['GET'])
@require_admin
def record_list():
    """修复记录列表 - 支持分页和筛选"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    mode = request.args.get('mode', '')
    date = request.args.get('date', '')
    platform = request.args.get('platform', '')
    status = request.args.get('status', '')
    keyword = request.args.get('keyword', '').strip()

    records = MOCK_RECORDS.copy()

    # 模式筛选
    if mode:
        records = [r for r in records if r['mode'] == mode]

    # 日期筛选
    if date:
        records = [r for r in records if r['created_at'].startswith(date)]

    # 平台筛选
    if platform:
        records = [r for r in records if r['platform'] == platform]

    # 状态筛选
    if status:
        records = [r for r in records if r['status'] == status]

    # 关键词搜索
    if keyword:
        records = [r for r in records if keyword.lower() in r['user_nickname'].lower()
                   or keyword.lower() in r['id'].lower()]

    records.sort(key=lambda x: x['created_at'], reverse=True)

    total = len(records)
    start = (page - 1) * limit
    end = start + limit

    return api_response(data={
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "list": records[start:end]
    })


@admin_api_bp.route('/records/stats', methods=['GET'])
@require_admin
def record_stats():
    """记录统计"""
    total = len(MOCK_RECORDS)
    success = sum(1 for r in MOCK_RECORDS if r['status'] == 'success')
    failed = sum(1 for r in MOCK_RECORDS if r['status'] == 'failed')
    processing = sum(1 for r in MOCK_RECORDS if r['status'] == 'processing')

    # 各模式统计
    mode_stats = {}
    for mode in MODES:
        mode_records = [r for r in MOCK_RECORDS if r['mode'] == mode]
        mode_stats[mode] = {
            "name": MODE_NAMES[mode],
            "total": len(mode_records),
            "success": sum(1 for r in mode_records if r['status'] == 'success'),
            "avg_duration": round(sum(r['duration'] for r in mode_records) / len(mode_records), 1) if mode_records else 0
        }

    # 各平台统计
    platform_stats = {}
    for p in PLATFORMS:
        platform_records = [r for r in MOCK_RECORDS if r['platform'] == p]
        platform_stats[p] = len(platform_records)

    return api_response(data={
        "total": total,
        "success": success,
        "failed": failed,
        "processing": processing,
        "success_rate": round(success / total * 100, 1) if total else 0,
        "mode_stats": mode_stats,
        "platform_stats": platform_stats,
        "today_count": sum(1 for r in MOCK_RECORDS if r['created_at'].startswith(datetime.now().strftime("%Y-%m-%d"))),
        "week_count": sum(1 for r in MOCK_RECORDS
                         if datetime.strptime(r['created_at'], "%Y-%m-%d %H:%M:%S") > datetime.now() - timedelta(days=7))
    })


# ============================================================
# 系统设置路由
# ============================================================

@admin_api_bp.route('/settings', methods=['GET'])
@require_admin
def get_settings():
    """获取系统设置"""
    return api_response(data=SYSTEM_SETTINGS)


@admin_api_bp.route('/settings', methods=['POST'])
@require_admin
def update_settings():
    """更新系统设置"""
    data = request.get_json() or {}

    allowed_keys = [
        "free_daily_limit", "member_price_monthly", "member_price_quarterly",
        "member_price_yearly", "member_daily_limit", "wechat_enabled",
        "alipay_enabled", "douyin_enabled", "qq_enabled",
        "colorize_enabled", "repair_enabled", "enhance_enabled",
        "denoise_enabled", "max_image_size", "support_email", "system_notice"
    ]

    for key in allowed_keys:
        if key in data:
            SYSTEM_SETTINGS[key] = data[key]

    return api_response(message="设置已更新")


# ============================================================
# 配额管理路由
# ============================================================

@admin_api_bp.route('/quota', methods=['GET'])
@require_admin
def get_quota():
    """各平台配额状态"""
    return api_response(data=PLATFORM_QUOTA)
