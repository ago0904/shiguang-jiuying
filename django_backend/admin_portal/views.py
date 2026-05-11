"""
管理后台API模块
拾光旧影 - 管理后台接口
提供完整的后台管理功能：认证、数据看板、用户管理、修复记录、系统设置、配额管理
"""

import time
import uuid
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum

from core.decorators import admin_required
from core.utils import json_response, error_response
from users.models import User
from api.models import RepairRecord
from stats.services import get_dashboard_data, get_trend_data
from stats.models import DailyStats, HourlyStats

logger = logging.getLogger(__name__)

# ============================================================
# 管理员Token存储（生产环境建议改用Redis或数据库）
# ============================================================

# Token存储 {token: {"username": ..., "role": ..., "expire_time": ...}}
ADMIN_TOKENS = {}

# 管理员账号配置
ADMIN_ACCOUNTS = getattr(settings, 'ADMIN_ACCOUNTS', {
    "admin": {
        "password": "admin123",
        "role": "super_admin",
        "name": "超级管理员"
    }
})


# ============================================================
# 管理后台页面
# ============================================================

def admin_page(request):
    """返回管理后台HTML页面"""
    return render(request, 'admin.html')


# ============================================================
# 认证API
# ============================================================

@csrf_exempt
@require_POST
def admin_login(request):
    """管理员登录
    
    POST /admin/api/login
    Body: {"username": "xxx", "password": "xxx"}
    """
    import json
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return error_response("请求格式错误", code=400)
    
    username = body.get('username', '').strip()
    password = body.get('password', '')
    
    if not username or not password:
        return error_response("用户名和密码不能为空", code=400)
    
    admin = ADMIN_ACCOUNTS.get(username)
    if not admin or admin['password'] != password:
        logger.warning(f"管理员登录失败: username={username}")
        return error_response("用户名或密码错误", code=401)
    
    # 生成Token
    token = uuid.uuid4().hex
    ADMIN_TOKENS[token] = {
        "username": username,
        "role": admin['role'],
        "expire_time": time.time() + 7200  # 2小时有效期
    }
    
    logger.info(f"管理员登录成功: username={username}")
    return json_response(data={
        "token": token,
        "username": username,
        "role": admin['role'],
        "name": admin['name'],
        "expire_in": 7200
    }, message="登录成功")


@require_GET
@admin_required
def admin_check(request):
    """检查登录状态
    
    GET /admin/api/check
    Header: X-Admin-Token: <token>
    """
    admin_token = request.META.get('HTTP_X_ADMIN_TOKEN', '')
    token_info = ADMIN_TOKENS.get(admin_token, {})
    admin = ADMIN_ACCOUNTS.get(token_info.get('username', ''), {})
    
    return json_response(data={
        "username": token_info.get('username', ''),
        "role": token_info.get('role', ''),
        "name": admin.get('name', ''),
        "expire_in": int(token_info.get('expire_time', 0) - time.time())
    })


# ============================================================
# 数据看板API
# ============================================================

@require_GET
@admin_required
def dashboard(request):
    """看板数据汇总
    
    GET /admin/api/dashboard
    Header: X-Admin-Token: <token>
    """
    # 从统计服务获取基础数据
    data = get_dashboard_data()
    
    # 总用户数
    total_users = User.objects.count()
    total_repairs = RepairRecord.objects.count()
    member_users = User.objects.filter(is_member=True).count()
    
    # 今日数据
    today = datetime.now().strftime('%Y-%m-%d')
    today_repairs = RepairRecord.objects.filter(
        created_at__date=today
    ).count() if hasattr(RepairRecord.objects.filter(created_at__date=today), 'count') else 0
    
    # 最新修复记录
    latest_records = RepairRecord.objects.select_related('user').order_by('-created_at')[:10]
    records_list = []
    for r in latest_records:
        records_list.append({
            'id': r.id,
            'user_id': r.user_id,
            'user_nickname': r.user.nickname if r.user else '',
            'mode': r.mode,
            'mode_name': r.mode_name,
            'platform': r.platform,
            'status': r.status,
            'cost_time': r.cost_time,
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M:%S') if r.created_at else '',
        })
    
    # 最新注册用户
    latest_users = User.objects.order_by('-created_at')[:10]
    users_list = [u.to_dict() for u in latest_users]
    
    data.update({
        'total_users': total_users,
        'total_repairs': total_repairs,
        'member_users': member_users,
        'today_repairs': today_repairs,
        'latest_records': records_list,
        'latest_users': users_list,
    })
    
    return json_response(data=data)


# ============================================================
# 用户管理API
# ============================================================

@require_GET
@admin_required
def user_list(request):
    """用户列表 - 支持分页和搜索
    
    GET /admin/api/users?page=1&limit=20&keyword=xxx&status=active
    Header: X-Admin-Token: <token>
    """
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    keyword = request.GET.get('keyword', '').strip()
    status = request.GET.get('status', '')
    
    # 构建查询
    queryset = User.objects.all()
    
    # 关键词搜索
    if keyword:
        queryset = queryset.filter(
            Q(nickname__icontains=keyword) |
            Q(id__icontains=keyword)
        )
    
    # 状态过滤
    if status:
        queryset = queryset.filter(status=status)
    
    # 排序
    queryset = queryset.order_by('-created_at')
    
    # 分页
    paginator = Paginator(queryset, limit)
    page_obj = paginator.get_page(page)
    
    users_list = [u.to_dict() for u in page_obj.object_list]
    
    return json_response(data={
        "total": paginator.count,
        "page": page,
        "limit": limit,
        "pages": paginator.num_pages,
        "list": users_list
    })


@require_GET
@admin_required
def user_detail(request, user_id):
    """用户详情
    
    GET /admin/api/users/<id>
    Header: X-Admin-Token: <token>
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return error_response("用户不存在", code=404)
    
    user_data = user.to_dict()
    
    # 获取用户修复统计
    repair_stats = RepairRecord.objects.filter(user=user).aggregate(
        total=Count('id'),
        success=Count('id', filter=Q(status='success')),
        failed=Count('id', filter=Q(status='failed')),
    )
    user_data['repair_stats'] = {
        'total': repair_stats.get('total', 0),
        'success': repair_stats.get('success', 0),
        'failed': repair_stats.get('failed', 0),
    }
    
    return json_response(data=user_data)


@csrf_exempt
@require_POST
@admin_required
def user_status(request, user_id):
    """修改用户状态（启用/禁用）
    
    POST /admin/api/users/<id>/status
    Body: {"status": "active" | "banned"}
    Header: X-Admin-Token: <token>
    """
    import json
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return error_response("请求格式错误", code=400)
    
    status = body.get('status', '')
    
    if status not in ['active', 'banned']:
        return error_response("状态参数错误，应为 active 或 banned", code=400)
    
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return error_response("用户不存在", code=404)
    
    user.status = status
    user.save()
    
    action = "启用" if status == 'active' else "禁用"
    logger.info(f"用户状态变更: user={user_id[:16]}, status={status}")
    return json_response(message=f"用户已{action}")


@csrf_exempt
@require_POST
@admin_required
def user_member(request, user_id):
    """设置会员状态
    
    POST /admin/api/users/<id>/member
    Body: {"is_member": true, "expire_days": 30}
    Header: X-Admin-Token: <token>
    """
    import json
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return error_response("请求格式错误", code=400)
    
    is_member = body.get('is_member', False)
    expire_days = body.get('expire_days', 30)
    
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return error_response("用户不存在", code=404)
    
    user.is_member = is_member
    if is_member:
        user.member_expire = datetime.now() + timedelta(days=expire_days)
    else:
        user.member_expire = None
    user.save()
    
    action = "设为会员" if is_member else "取消会员"
    logger.info(f"用户会员变更: user={user_id[:16]}, is_member={is_member}")
    return json_response(message=f"已{action}")


@require_GET
@admin_required
def user_history(request, user_id):
    """用户修复历史
    
    GET /admin/api/users/<id>/history?page=1&limit=20
    Header: X-Admin-Token: <token>
    """
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return error_response("用户不存在", code=404)
    
    records = RepairRecord.objects.filter(user=user).order_by('-created_at')
    paginator = Paginator(records, limit)
    page_obj = paginator.get_page(page)
    
    records_list = [r.to_dict() for r in page_obj.object_list]
    
    return json_response(data={
        "total": paginator.count,
        "page": page,
        "limit": limit,
        "pages": paginator.num_pages,
        "list": records_list
    })


# ============================================================
# 修复记录API
# ============================================================

@require_GET
@admin_required
def record_list(request):
    """修复记录列表 - 支持分页和筛选
    
    GET /admin/api/records?page=1&limit=20&mode=colorize&status=success
    Header: X-Admin-Token: <token>
    """
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    mode = request.GET.get('mode', '')
    date_str = request.GET.get('date', '')
    platform = request.GET.get('platform', '')
    status = request.GET.get('status', '')
    keyword = request.GET.get('keyword', '').strip()
    
    # 构建查询
    queryset = RepairRecord.objects.select_related('user')
    
    # 模式筛选
    if mode:
        queryset = queryset.filter(mode=mode)
    
    # 日期筛选
    if date_str:
        queryset = queryset.filter(created_at__date=date_str)
    
    # 平台筛选
    if platform:
        queryset = queryset.filter(platform=platform)
    
    # 状态筛选
    if status:
        queryset = queryset.filter(status=status)
    
    # 关键词搜索
    if keyword:
        queryset = queryset.filter(
            Q(user__nickname__icontains=keyword) |
            Q(id__icontains=keyword)
        )
    
    queryset = queryset.order_by('-created_at')
    
    # 分页
    paginator = Paginator(queryset, limit)
    page_obj = paginator.get_page(page)
    
    records_list = [r.to_dict() for r in page_obj.object_list]
    
    return json_response(data={
        "total": paginator.count,
        "page": page,
        "limit": limit,
        "pages": paginator.num_pages,
        "list": records_list
    })


@require_GET
@admin_required
def record_stats(request):
    """记录统计
    
    GET /admin/api/records/stats
    Header: X-Admin-Token: <token>
    """
    total = RepairRecord.objects.count()
    success = RepairRecord.objects.filter(status='success').count()
    failed = RepairRecord.objects.filter(status='failed').count()
    processing = RepairRecord.objects.filter(status='processing').count()
    
    # 各模式统计
    mode_stats = {}
    MODE_NAMES = {
        'colorize': '上色',
        'repair': '修复',
        'enhance': '增强',
        'denoise': '去噪',
    }
    for mode, mode_name in MODE_NAMES.items():
        mode_records = RepairRecord.objects.filter(mode=mode)
        mode_stats[mode] = {
            "name": mode_name,
            "total": mode_records.count(),
            "success": mode_records.filter(status='success').count(),
        }
    
    return json_response(data={
        "total": total,
        "success": success,
        "failed": failed,
        "processing": processing,
        "success_rate": round(success / total * 100, 1) if total else 0,
        "mode_stats": mode_stats,
    })


# ============================================================
# 系统设置API
# ============================================================

@require_GET
@admin_required
def get_settings(request):
    """获取系统设置
    
    GET /admin/api/settings
    Header: X-Admin-Token: <token>
    """
    from django.conf import settings as django_settings
    
    system_settings = {
        "free_daily_limit": getattr(django_settings, 'FREE_DAILY_LIMIT', 3),
        "member_price_monthly": getattr(django_settings, 'MEMBER_PRICE_MONTHLY', 19.9),
        "member_price_quarterly": getattr(django_settings, 'MEMBER_PRICE_QUARTERLY', 49.9),
        "member_price_yearly": getattr(django_settings, 'MEMBER_PRICE_YEARLY', 169.9),
        "member_daily_limit": getattr(django_settings, 'MEMBER_DAILY_LIMIT', 50),
        "max_image_size": getattr(django_settings, 'MAX_IMAGE_SIZE', 10),
        "support_email": getattr(django_settings, 'SUPPORT_EMAIL', ''),
        "system_notice": getattr(django_settings, 'SYSTEM_NOTICE', ''),
        "wechat_appid": getattr(django_settings, 'WECHAT_APPID', ''),
    }
    
    return json_response(data=system_settings)


@csrf_exempt
@require_POST
@admin_required
def update_settings(request):
    """更新系统设置
    
    POST /admin/api/settings
    Body: {"free_daily_limit": 3, "max_image_size": 10, ...}
    Header: X-Admin-Token: <token>
    """
    import json
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return error_response("请求格式错误", code=400)
    
    # 允许更新的设置项
    allowed_keys = [
        "free_daily_limit", "member_price_monthly", "member_price_quarterly",
        "member_price_yearly", "member_daily_limit", "max_image_size",
        "support_email", "system_notice"
    ]
    
    updated = []
    for key in allowed_keys:
        if key in body:
            # 实际项目中应该保存到数据库或配置文件
            updated.append(key)
    
    logger.info(f"系统设置已更新: {updated}")
    return json_response(message="设置已更新")


# ============================================================
# 配额管理API
# ============================================================

@require_GET
@admin_required
def get_quota(request):
    """各平台配额状态
    
    GET /admin/api/quota
    Header: X-Admin-Token: <token>
    """
    # 各平台配额信息（实际项目中从数据库或外部API获取）
    platform_quota = {
        "baidu": {
            "name": "百度AI",
            "quota": 5000,
            "used": DailyStats.objects.aggregate(s=Sum('platform_baidu'))['s'] or 0,
            "remaining": 5000 - (DailyStats.objects.aggregate(s=Sum('platform_baidu'))['s'] or 0),
            "status": "normal",
            "expire": "2026-12-31"
        },
        "tencent": {
            "name": "腾讯云",
            "quota": 5000,
            "used": DailyStats.objects.aggregate(s=Sum('platform_tencent'))['s'] or 0,
            "remaining": 5000 - (DailyStats.objects.aggregate(s=Sum('platform_tencent'))['s'] or 0),
            "status": "normal",
            "expire": "2026-12-31"
        },
        "replicate": {
            "name": "Replicate",
            "quota": 3000,
            "used": DailyStats.objects.aggregate(s=Sum('platform_replicate'))['s'] or 0,
            "remaining": 3000 - (DailyStats.objects.aggregate(s=Sum('platform_replicate'))['s'] or 0),
            "status": "normal",
            "expire": "2026-12-31"
        },
    }
    
    return json_response(data=platform_quota)
