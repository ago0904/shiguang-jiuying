"""数据统计模块 - 自动收集和聚合

功能：
1. 修复请求追踪中间件（自动记录每次修复操作）
2. 每日数据聚合
3. 管理台数据看板API
4. 趋势分析

API路由：
- GET /api/stats/dashboard          - 管理台数据看板
- GET /api/stats/daily               - 每日统计查询
- GET /api/stats/hourly              - 今日24小时分布
- GET /api/stats/mode_distribution   - 模式分布
- GET /api/stats/platform_distribution - 平台分布
- POST /api/stats/track              - 手动记录修复操作（调试用）
"""

import uuid
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

from flask import Blueprint, request, g

from config import Config
from models import (
    user_dao, record_dao, stats_dao,
    RepairRecord, now_str, today_str
)
from auth import login_required, admin_required, success_response, error_response

# ─────────────────────────────────────────────
# 日志
# ─────────────────────────────────────────────

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 创建蓝图
# ─────────────────────────────────────────────

stats_bp = Blueprint('stats', __name__, url_prefix='/api/stats')

# ─────────────────────────────────────────────
# 修复模式名称映射
# ─────────────────────────────────────────────

MODE_NAMES = {
    'colorize': '黑白上色',
    'restore': '破损修复',
    'enhance': '清晰度增强',
    'denoise': '噪点去除',
    'scratch': '划痕修复',
    'general': '综合修复',
}

PLATFORM_NAMES = {
    'baidu': '百度AI',
    'aliyun': '阿里云',
    'tencent': '腾讯云',
    'local': '本地模型',
}


# ─────────────────────────────────────────────
# 追踪中间件
# ─────────────────────────────────────────────


def track_repair(user_id: str, mode: str, platform: str, cost_time: float = 0.0):
    """记录一次修复操作

    每次修复请求完成后调用，自动记录到历史数据

    Args:
        user_id: 用户ID
        mode: 修复模式 (colorize/restore/enhance/...)
        platform: 使用的AI平台 (baidu/aliyun/tencent/...)
        cost_time: 耗时（秒）
    """
    try:
        # 获取IP地址
        ip = request.remote_addr or ''
        if request.headers.get('X-Forwarded-For'):
            ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()

        mode_name = MODE_NAMES.get(mode, mode)

        record = record_dao.create(
            user_id=user_id,
            mode=mode,
            mode_name=mode_name,
            platform=platform,
            cost_time=cost_time,
            ip=ip
        )

        # 增加用户修复次数
        user_dao.increment_repair(user_id)

        logger.info(
            f"记录修复: user={user_id}, mode={mode}, "
            f"platform={platform}, cost={cost_time:.2f}s"
        )
        return record

    except Exception as e:
        logger.error(f"记录修复操作失败: {e}", exc_info=True)
        return None


def track_repair_from_request(mode: str, platform: str, cost_time: float = 0.0):
    """从当前请求上下文记录修复操作

    需要在使用了 @login_required 装饰器的接口中调用

    Args:
        mode: 修复模式
        platform: AI平台
        cost_time: 耗时
    """
    try:
        user = g.get('current_user')
        if not user:
            logger.warning("记录修复操作失败: 当前请求无用户信息")
            return None
        return track_repair(user.id, mode, platform, cost_time)
    except Exception as e:
        logger.error(f"从请求记录修复操作失败: {e}")
        return None


# ─────────────────────────────────────────────
# 数据聚合
# ─────────────────────────────────────────────


def aggregate_daily(date: str = None) -> dict:
    """聚合指定日期的统计数据

    从历史记录中聚合生成当日的统计数据

    Args:
        date: 日期字符串 YYYY-MM-DD，默认为今天

    Returns:
        DailyStats字典
    """
    date = date or today_str()

    try:
        # 获取当天的所有修复记录
        all_records = record_dao.get_all()
        day_records = [r for r in all_records if r.created_at.startswith(date)]

        # 聚合统计
        stats = stats_dao.aggregate_from_records(date, day_records)

        # 计算新用户数
        # 新用户 = 当天注册的用户
        stats.new_users = user_dao.count_today_new()

        stats_dao.save(stats)

        logger.info(
            f"聚合统计完成: date={date}, repairs={stats.total_repairs}, "
            f"users={stats.unique_users}, new_users={stats.new_users}"
        )
        return stats.to_dict()

    except Exception as e:
        logger.error(f"聚合统计失败: {e}", exc_info=True)
        return {}


def aggregate_today() -> dict:
    """聚合今日统计数据"""
    return aggregate_daily(today_str())


def get_dashboard_summary() -> dict:
    """获取看板汇总数据

    Returns:
        dict: 包含今日数据、累计数据、趋势数据
    """
    today = today_str()

    # 确保今日统计已聚合
    today_stats = stats_dao.get_or_create(today)
    if today_stats.total_repairs == 0:
        # 尝试从记录重新聚合
        today_stats_data = aggregate_daily(today)
        today_stats = stats_dao.get_or_create(today)

    # 今日数据
    today_data = {
        'date': today,
        'total_repairs': today_stats.total_repairs,
        'unique_users': today_stats.unique_users,
        'new_users': today_stats.new_users,
        'avg_cost_time': today_stats.avg_cost_time,
        'errors': today_stats.errors,
    }

    # 累计数据
    total_users = user_dao.count()
    total_repairs = record_dao.count()
    active_users = user_dao.count_active()

    # 近7天趋势
    trend_7d = get_trend(days=7)

    # 模式分布（今日）
    mode_dist = today_stats.mode_breakdown or {}
    # 填充所有模式
    mode_distribution = {}
    for key, name in MODE_NAMES.items():
        mode_distribution[name] = mode_dist.get(key, 0)

    # 平台分布（今日）
    platform_dist = today_stats.platform_breakdown or {}
    platform_distribution = {}
    for key, name in PLATFORM_NAMES.items():
        platform_distribution[name] = platform_dist.get(key, 0)

    # 近30天汇总
    last_30d = get_trend(days=30)
    total_repairs_30d = sum(day.get('total_repairs', 0) for day in last_30d)
    total_users_30d = sum(day.get('unique_users', 0) for day in last_30d)

    return {
        'today': today_data,
        'total': {
            'total_users': total_users,
            'total_repairs': total_repairs,
            'active_users': active_users,
        },
        'recent_30d': {
            'total_repairs': total_repairs_30d,
            'total_active_users': total_users_30d,
        },
        'trend_7d': trend_7d,
        'mode_distribution': mode_distribution,
        'platform_distribution': platform_distribution,
    }


def get_trend(days: int = 7) -> list:
    """获取趋势数据

    Args:
        days: 天数，默认7天

    Returns:
        list: 每日统计数据列表
    """
    stats_list = stats_dao.get_recent(days)
    return [s.to_dict() for s in stats_list]


# ─────────────────────────────────────────────
# API路由
# ─────────────────────────────────────────────


@stats_bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard():
    """管理台数据看板

    返回完整的看板数据，包括：
    - 今日修复次数
    - 今日独立用户
    - 今日新用户
    - 总用户、总修复次数
    - 近7天趋势
    - 模式分布、平台分布

    请求头:
        Authorization: Bearer <Token> (需要管理员权限)

    响应:
        {
            "code": 0,
            "message": "成功",
            "data": {
                "today": {
                    "date": "2024-01-15",
                    "total_repairs": 128,
                    "unique_users": 56,
                    "new_users": 12,
                    "avg_cost_time": 3.5,
                    "errors": 0
                },
                "total": {
                    "total_users": 1500,
                    "total_repairs": 8500,
                    "active_users": 1200
                },
                "recent_30d": {
                    "total_repairs": 3500,
                    "total_active_users": 800
                },
                "trend_7d": [
                    {"date": "2024-01-09", "total_repairs": 95, ...},
                    {"date": "2024-01-10", "total_repairs": 110, ...},
                    ...
                ],
                "mode_distribution": {
                    "黑白上色": 45,
                    "破损修复": 30,
                    "清晰度增强": 25,
                    ...
                },
                "platform_distribution": {
                    "百度AI": 80,
                    "阿里云": 48,
                    ...
                }
            },
            "timestamp": 1700000000
        }
    """
    try:
        # 先聚合今日数据
        aggregate_today()

        # 获取看板数据
        summary = get_dashboard_summary()

        return success_response(summary, message="成功")

    except Exception as e:
        logger.error(f"获取看板数据异常: {e}", exc_info=True)
        return error_response("获取看板数据失败", code=500)


@stats_bp.route('/daily', methods=['GET'])
@admin_required
def daily_stats():
    """每日统计查询

    查询指定日期范围的每日统计数据

    查询参数:
        start: 开始日期 YYYY-MM-DD (可选，默认7天前)
        end: 结束日期 YYYY-MM-DD (可选，默认今天)

    响应:
        {
            "code": 0,
            "message": "成功",
            "data": {
                "list": [
                    {
                        "date": "2024-01-01",
                        "total_repairs": 100,
                        "unique_users": 50,
                        "new_users": 10,
                        "mode_breakdown": {"colorize": 60, ...},
                        "platform_breakdown": {"baidu": 80, ...},
                        "avg_cost_time": 3.2,
                        "errors": 2
                    }
                ]
            },
            "timestamp": 1700000000
        }
    """
    try:
        # 获取查询参数
        end_date = request.args.get('end', today_str())
        start_date = request.args.get(
            'start',
            (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        )

        # 参数校验
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return error_response("日期格式错误，应为 YYYY-MM-DD", code=400, status_code=400)

        if start_date > end_date:
            return error_response("开始日期不能大于结束日期", code=400, status_code=400)

        # 限制查询范围不超过90天
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        if (end_dt - start_dt).days > 90:
            return error_response("查询范围不能超过90天", code=400, status_code=400)

        # 获取数据
        stats_list = stats_dao.get_date_range(start_date, end_date)

        # 对于缺失的日期，从记录中聚合
        if not stats_list:
            # 尝试从记录中聚合
            all_records = record_dao.get_all()
            filtered = [r for r in all_records if start_date <= r.created_at[:10] <= end_date]

            # 按日期分组
            date_groups = {}
            for r in filtered:
                d = r.created_at[:10]
                if d not in date_groups:
                    date_groups[d] = []
                date_groups[d].append(r)

            stats_list = []
            for d in sorted(date_groups.keys()):
                stats = stats_dao.aggregate_from_records(d, date_groups[d])
                stats_list.append(stats)

        return success_response({
            'list': [s.to_dict() for s in stats_list],
            'start': start_date,
            'end': end_date,
            'total': len(stats_list)
        }, message="成功")

    except Exception as e:
        logger.error(f"查询每日统计异常: {e}", exc_info=True)
        return error_response("查询失败", code=500)


@stats_bp.route('/hourly', methods=['GET'])
@admin_required
def hourly_stats():
    """今日24小时分布

    获取今日每个小时的修复次数分布

    响应:
        {
            "code": 0,
            "message": "成功",
            "data": {
                "date": "2024-01-15",
                "hours": [0, 0, 0, 0, 2, 5, 8, 15, 20, ...],
                "labels": ["00:00", "01:00", ..., "23:00"]
            },
            "timestamp": 1700000000
        }
    """
    try:
        # 生成24小时数据
        hourly = record_dao.get_today_hourly()

        labels = [f"{h:02d}:00" for h in range(24)]

        return success_response({
            'date': today_str(),
            'hours': hourly,
            'labels': labels,
            'total': sum(hourly)
        }, message="成功")

    except Exception as e:
        logger.error(f"获取24小时分布异常: {e}", exc_info=True)
        return error_response("查询失败", code=500)


@stats_bp.route('/mode_distribution', methods=['GET'])
@admin_required
def mode_distribution():
    """修复模式分布统计

    查询参数:
        date: 日期 YYYY-MM-DD (可选，默认今天)

    响应:
        {
            "code": 0,
            "message": "成功",
            "data": {
                "date": "2024-01-15",
                "distribution": {
                    "黑白上色": 45,
                    "破损修复": 30,
                    "清晰度增强": 25,
                    "噪点去除": 15,
                    "划痕修复": 8,
                    "综合修复": 5
                }
            },
            "timestamp": 1700000000
        }
    """
    try:
        date = request.args.get('date', today_str())

        # 校验日期格式
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return error_response("日期格式错误", code=400, status_code=400)

        # 获取或聚合数据
        stats = stats_dao.get_by_date(date)
        if not stats or not stats.mode_breakdown:
            # 从记录聚合
            all_records = record_dao.get_all()
            day_records = [r for r in all_records if r.created_at.startswith(date)]
            stats = stats_dao.aggregate_from_records(date, day_records)

        # 填充所有模式
        distribution = {}
        mode_breakdown = stats.mode_breakdown or {}
        for key, name in MODE_NAMES.items():
            distribution[name] = mode_breakdown.get(key, 0)

        return success_response({
            'date': date,
            'distribution': distribution,
            'total': sum(distribution.values())
        }, message="成功")

    except Exception as e:
        logger.error(f"获取模式分布异常: {e}", exc_info=True)
        return error_response("查询失败", code=500)


@stats_bp.route('/platform_distribution', methods=['GET'])
@admin_required
def platform_distribution():
    """AI平台分布统计

    查询参数:
        date: 日期 YYYY-MM-DD (可选，默认今天)

    响应:
        {
            "code": 0,
            "message": "成功",
            "data": {
                "date": "2024-01-15",
                "distribution": {
                    "百度AI": 80,
                    "阿里云": 48,
                    "腾讯云": 0,
                    "本地模型": 0
                }
            },
            "timestamp": 1700000000
        }
    """
    try:
        date = request.args.get('date', today_str())

        # 校验日期格式
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return error_response("日期格式错误", code=400, status_code=400)

        # 获取或聚合数据
        stats = stats_dao.get_by_date(date)
        if not stats or not stats.platform_breakdown:
            all_records = record_dao.get_all()
            day_records = [r for r in all_records if r.created_at.startswith(date)]
            stats = stats_dao.aggregate_from_records(date, day_records)

        # 填充所有平台
        distribution = {}
        platform_breakdown = stats.platform_breakdown or {}
        for key, name in PLATFORM_NAMES.items():
            distribution[name] = platform_breakdown.get(key, 0)

        return success_response({
            'date': date,
            'distribution': distribution,
            'total': sum(distribution.values())
        }, message="成功")

    except Exception as e:
        logger.error(f"获取平台分布异常: {e}", exc_info=True)
        return error_response("查询失败", code=500)


@stats_bp.route('/track', methods=['POST'])
@login_required
def track_manual():
    """手动记录修复操作（调试用）

    请求体:
        {
            "mode": "colorize",
            "platform": "baidu",
            "cost_time": 3.5
        }

    响应:
        {
            "code": 0,
            "message": "记录成功",
            "data": {"record_id": "xxx"},
            "timestamp": 1700000000
        }
    """
    try:
        data = request.get_json(silent=True) or {}

        mode = data.get('mode', 'general')
        platform = data.get('platform', 'baidu')
        cost_time = data.get('cost_time', 0.0)

        record = track_repair_from_request(mode, platform, cost_time)

        if record:
            return success_response({
                'record_id': record.id
            }, message="记录成功")
        else:
            return error_response("记录失败", code=500)

    except Exception as e:
        logger.error(f"手动记录异常: {e}", exc_info=True)
        return error_response("记录失败", code=500)


@stats_bp.route('/user_repair_history', methods=['GET'])
@login_required
def user_repair_history():
    """获取当前用户的修复历史

    查询参数:
        limit: 返回条数 (可选，默认50)

    响应:
        {
            "code": 0,
            "message": "成功",
            "data": {
                "list": [
                    {
                        "id": "xxx",
                        "mode": "colorize",
                        "mode_name": "黑白上色",
                        "platform": "baidu",
                        "cost_time": 3.5,
                        "created_at": "2024-01-15 12:00:00"
                    }
                ],
                "total": 100
            },
            "timestamp": 1700000000
        }
    """
    try:
        user = g.current_user
        limit = request.args.get('limit', 50, type=int)

        # 限制最大条数
        if limit > 200:
            limit = 200

        records = record_dao.get_by_user(user.id, limit=limit)

        return success_response({
            'list': [r.to_dict() for r in records],
            'total': len(records)
        }, message="成功")

    except Exception as e:
        logger.error(f"获取修复历史异常: {e}", exc_info=True)
        return error_response("查询失败", code=500)


# ─────────────────────────────────────────────
# 初始化聚合
# ─────────────────────────────────────────────


def init_stats():
    """初始化统计数据

    在应用启动时调用，确保今日统计数据已初始化
    """
    try:
        today = today_str()
        stats = stats_dao.get_or_create(today)
        logger.info(f"统计数据初始化完成: date={today}")

        # 如果今日统计为空，尝试聚合
        if stats.total_repairs == 0:
            aggregate_daily(today)

    except Exception as e:
        logger.error(f"统计数据初始化失败: {e}")


# ─────────────────────────────────────────────
# 后台定时任务（可选）
# ─────────────────────────────────────────────


def run_daily_aggregation():
    """每日定时聚合任务

    可以在Flask-APScheduler中配置为每日凌晨执行
    """
    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        # 聚合昨天的数据
        aggregate_daily(yesterday)
        logger.info(f"昨日数据聚合完成: {yesterday}")

        # 同时聚合今天的数据（确保今日数据最新）
        aggregate_daily(today_str())

    except Exception as e:
        logger.error(f"每日聚合任务异常: {e}", exc_info=True)
