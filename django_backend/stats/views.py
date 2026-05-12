"""
统计模块 - API 视图
提供数据看板、每日统计、每小时统计、模式分布等接口
"""
import logging
from datetime import datetime, timedelta
from django.db.models import Count, F
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from core.utils import success_response, error_response, today, now
from core.decorators import login_required, admin_required
from stats.models import DailyStats, HourlyStats
from api.models import RepairRecord
from users.models import User

logger = logging.getLogger('api')


# ============================================================
# 1. 数据看板（需管理员权限）
# ============================================================

@require_http_methods(["GET"])
@admin_required
def dashboard(request):
    """
    GET /api/stats/dashboard
    管理员数据看板
    返回今日概览、7天趋势、模式分布、24小时分布等
    """
    try:
        logger.info("[StatsDashboard] 管理员请求数据看板")
        
        today_date = today()
        
        # 今日概览
        today_stats = _get_today_overview(today_date)
        
        # 7天趋势
        trend_7d = _get_7day_trend(today_date)
        
        # 今日模式分布
        mode_distribution = _get_today_mode_distribution(today_date)
        
        # 今日平台分布
        platform_distribution = _get_today_platform_distribution(today_date)
        
        # 24小时分布
        hourly_distribution = _get_hourly_distribution(today_date)
        
        # 用户统计
        user_stats = _get_user_stats()
        
        data = {
            "today": today_stats,
            "trend_7d": trend_7d,
            "mode_distribution": mode_distribution,
            "platform_distribution": platform_distribution,
            "hourly_distribution": hourly_distribution,
            "user_stats": user_stats,
            "update_time": now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        return success_response(data=data, message="获取成功")
    
    except Exception as e:
        logger.error(f"[StatsDashboard] 获取看板数据失败: {e}", exc_info=True)
        return error_response(f"获取看板数据失败: {str(e)}", code=500)


def _get_today_overview(today_date):
    """获取今日概览数据"""
    try:
        today_record = DailyStats.objects.filter(date=today_date).first()
        
        # 今日实时统计（从 RepairRecord 直接计算）
        today_repair_count = RepairRecord.objects.filter(
            created_at__date=today_date
        ).count()
        
        today_success_count = RepairRecord.objects.filter(
            created_at__date=today_date,
            is_success=True
        ).count()
        
        today_user_count = RepairRecord.objects.filter(
            created_at__date=today_date,
            user__isnull=False
        ).values('user').distinct().count()
        
        if today_record:
            return {
                "total_repairs": today_record.total_repairs,
                "unique_users": today_record.unique_users,
                "new_users": today_record.new_users,
                "success_rate": round(today_success_count / max(today_repair_count, 1) * 100, 1),
                "avg_cost_time": today_record.avg_cost_time,
                "errors": today_record.errors,
                "mode_total": {
                    "colorize": today_record.mode_colorize,
                    "repair": today_record.mode_repair,
                    "enhance": today_record.mode_enhance,
                    "denoise": today_record.mode_denoise,
                },
            }
        else:
            return {
                "total_repairs": today_repair_count,
                "unique_users": today_user_count,
                "new_users": 0,
                "success_rate": round(today_success_count / max(today_repair_count, 1) * 100, 1),
                "avg_cost_time": 0.0,
                "errors": 0,
                "mode_total": {"colorize": 0, "repair": 0, "enhance": 0, "denoise": 0},
            }
    except Exception as e:
        logger.warning(f"[Stats] 获取今日概览失败: {e}")
        return {
            "total_repairs": 0,
            "unique_users": 0,
            "new_users": 0,
            "success_rate": 0,
            "avg_cost_time": 0.0,
            "errors": 0,
            "mode_total": {"colorize": 0, "repair": 0, "enhance": 0, "denoise": 0},
        }


def _get_7day_trend(today_date):
    """获取7天趋势数据"""
    try:
        start_date = today_date - timedelta(days=6)
        
        # 获取数据库中已有的统计
        stats = DailyStats.objects.filter(
            date__gte=start_date,
            date__lte=today_date
        ).order_by('date')
        
        # 补全缺失的日期
        date_map = {s.date: s for s in stats}
        result = []
        
        for i in range(7):
            date = start_date + timedelta(days=i)
            if date in date_map:
                s = date_map[date]
                result.append({
                    "date": str(date),
                    "total_repairs": s.total_repairs,
                    "unique_users": s.unique_users,
                    "new_users": s.new_users,
                    "errors": s.errors,
                })
            else:
                # 实时计算该日数据
                day_count = RepairRecord.objects.filter(
                    created_at__date=date
                ).count()
                day_users = RepairRecord.objects.filter(
                    created_at__date=date,
                    user__isnull=False
                ).values('user').distinct().count()
                
                result.append({
                    "date": str(date),
                    "total_repairs": day_count,
                    "unique_users": day_users,
                    "new_users": 0,
                    "errors": 0,
                })
        
        return result
    except Exception as e:
        logger.warning(f"[Stats] 获取7天趋势失败: {e}")
        return []


def _get_today_mode_distribution(today_date):
    """获取今日模式分布"""
    try:
        today_record = DailyStats.objects.filter(date=today_date).first()
        
        if today_record:
            return {
                "colorize": today_record.mode_colorize,
                "repair": today_record.mode_repair,
                "enhance": today_record.mode_enhance,
                "denoise": today_record.mode_denoise,
            }
        
        # 实时计算
        modes = RepairRecord.objects.filter(
            created_at__date=today_date
        ).values('mode').annotate(count=Count('id'))
        
        distribution = {"colorize": 0, "repair": 0, "enhance": 0, "denoise": 0}
        for item in modes:
            if item['mode'] in distribution:
                distribution[item['mode']] = item['count']
        
        return distribution
    except Exception as e:
        logger.warning(f"[Stats] 获取模式分布失败: {e}")
        return {"colorize": 0, "repair": 0, "enhance": 0, "denoise": 0}


def _get_today_platform_distribution(today_date):
    """获取今日平台分布"""
    try:
        today_record = DailyStats.objects.filter(date=today_date).first()
        
        if today_record:
            return {
                "baidu": today_record.platform_baidu,
                "tencent": today_record.platform_tencent,
                "replicate": today_record.platform_replicate,
            }
        
        # 实时计算
        platforms = RepairRecord.objects.filter(
            created_at__date=today_date
        ).values('platform').annotate(count=Count('id'))
        
        distribution = {"baidu": 0, "tencent": 0, "replicate": 0}
        for item in platforms:
            platform = item['platform'] or ''
            if platform in distribution:
                distribution[platform] = item['count']
        
        return distribution
    except Exception as e:
        logger.warning(f"[Stats] 获取平台分布失败: {e}")
        return {"baidu": 0, "tencent": 0, "replicate": 0}


def _get_hourly_distribution(today_date):
    """获取24小时分布"""
    try:
        hourly_stats = HourlyStats.objects.filter(
            date=today_date
        ).order_by('hour')
        
        # 构建24小时完整数据
        hour_map = {h.hour: h for h in hourly_stats}
        result = []
        
        for hour in range(24):
            if hour in hour_map:
                h = hour_map[hour]
                result.append({
                    "hour": hour,
                    "label": h.label,
                    "repairs": h.repairs,
                    "mode_distribution": {
                        "colorize": h.mode_colorize,
                        "repair": h.mode_repair,
                        "enhance": h.mode_enhance,
                        "denoise": h.mode_denoise,
                    },
                })
            else:
                result.append({
                    "hour": hour,
                    "label": f"{hour:02d}:00",
                    "repairs": 0,
                    "mode_distribution": {
                        "colorize": 0,
                        "repair": 0,
                        "enhance": 0,
                        "denoise": 0,
                    },
                })
        
        return result
    except Exception as e:
        logger.warning(f"[Stats] 获取小时分布失败: {e}")
        return [{"hour": h, "label": f"{h:02d}:00", "repairs": 0} for h in range(24)]


def _get_user_stats():
    """获取用户统计数据"""
    try:
        total_users = User.objects.count()
        today_date = today()
        new_users_today = User.objects.filter(created_at__date=today_date).count()
        active_users_today = RepairRecord.objects.filter(
            created_at__date=today_date,
            user__isnull=False
        ).values('user').distinct().count()
        member_count = User.objects.filter(is_member=True).count()
        
        return {
            "total_users": total_users,
            "new_users_today": new_users_today,
            "active_users_today": active_users_today,
            "member_count": member_count,
        }
    except Exception as e:
        logger.warning(f"[Stats] 获取用户统计失败: {e}")
        return {
            "total_users": 0,
            "new_users_today": 0,
            "active_users_today": 0,
            "member_count": 0,
        }


# ============================================================
# 2. 每日统计
# ============================================================

@require_http_methods(["GET"])
@admin_required
def daily_stats(request):
    """
    GET /api/stats/daily
    每日统计数据
    参数:
        - start: 开始日期 (YYYY-MM-DD)
        - end: 结束日期 (YYYY-MM-DD)
    """
    try:
        # 解析日期参数
        start_str = request.GET.get('start')
        end_str = request.GET.get('end')
        
        today_date = today()
        
        if start_str:
            try:
                start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            except ValueError:
                return error_response("start 日期格式错误，应为 YYYY-MM-DD", code=400, status=400)
        else:
            start_date = today_date - timedelta(days=30)
        
        if end_str:
            try:
                end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            except ValueError:
                return error_response("end 日期格式错误，应为 YYYY-MM-DD", code=400, status=400)
        else:
            end_date = today_date
        
        if start_date > end_date:
            return error_response("开始日期不能晚于结束日期", code=400, status=400)
        
        # 限制查询范围
        max_range = timedelta(days=365)
        if end_date - start_date > max_range:
            start_date = end_date - max_range
        
        logger.info(f"[DailyStats] 查询 {start_date} 到 {end_date}")
        
        # 查询数据库
        stats = DailyStats.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('-date')
        
        # 构建响应
        result = {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_days": (end_date - start_date).days + 1,
            "data_count": stats.count(),
            "summary": {
                "total_repairs": sum(s.total_repairs for s in stats),
                "total_users": sum(s.unique_users for s in stats),
                "total_new_users": sum(s.new_users for s in stats),
                "total_errors": sum(s.errors for s in stats),
                "avg_cost_time": round(
                    sum(s.avg_cost_time * s.total_repairs for s in stats) / max(sum(s.total_repairs for s in stats), 1), 2
                ),
            },
            "list": [s.to_dict() for s in stats]
        }
        
        return success_response(data=result, message="获取成功")
    
    except Exception as e:
        logger.error(f"[DailyStats] 获取每日统计失败: {e}", exc_info=True)
        return error_response(f"获取每日统计失败: {str(e)}", code=500)


# ============================================================
# 3. 今日24小时统计
# ============================================================

@require_http_methods(["GET"])
@admin_required
def hourly_stats(request):
    """
    GET /api/stats/hourly
    今日24小时统计数据
    """
    try:
        today_date = today()
        
        logger.info(f"[HourlyStats] 查询今日24小时分布: {today_date}")
        
        hourly_data = HourlyStats.objects.filter(
            date=today_date
        ).order_by('hour')
        
        # 补全24小时
        hour_map = {h.hour: h for h in hourly_data}
        result = []
        total_repairs = 0
        
        for hour in range(24):
            if hour in hour_map:
                h = hour_map[hour]
                result.append(h.to_dict())
                total_repairs += h.repairs
            else:
                result.append({
                    "date": str(today_date),
                    "hour": hour,
                    "label": f"{hour:02d}:00",
                    "repairs": 0,
                    "mode_distribution": {
                        "colorize": 0, "repair": 0, "enhance": 0, "denoise": 0
                    },
                })
        
        data = {
            "date": str(today_date),
            "total_repairs": total_repairs,
            "hours": result,
        }
        
        return success_response(data=data, message="获取成功")
    
    except Exception as e:
        logger.error(f"[HourlyStats] 获取小时统计失败: {e}", exc_info=True)
        return error_response(f"获取小时统计失败: {str(e)}", code=500)


# ============================================================
# 4. 模式分布
# ============================================================

@require_http_methods(["GET"])
@admin_required
def mode_distribution(request):
    """
    GET /api/stats/mode_distribution
    修复模式分布统计
    参数:
        - start: 开始日期 (可选)
        - end: 结束日期 (可选)
    """
    try:
        start_str = request.GET.get('start')
        end_str = request.GET.get('end')
        
        today_date = today()
        
        if start_str:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        else:
            start_date = today_date - timedelta(days=30)
        
        if end_str:
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        else:
            end_date = today_date
        
        # 从 DailyStats 汇总
        stats = DailyStats.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        
        mode_totals = {
            "colorize": sum(s.mode_colorize for s in stats),
            "repair": sum(s.mode_repair for s in stats),
            "enhance": sum(s.mode_enhance for s in stats),
            "denoise": sum(s.mode_denoise for s in stats),
        }
        
        grand_total = sum(mode_totals.values())
        
        mode_names = {
            "colorize": "黑白上色",
            "repair": "破损修复",
            "enhance": "清晰度增强",
            "denoise": "智能去噪",
        }
        
        # 计算百分比
        distribution = []
        for key, name in mode_names.items():
            count = mode_totals.get(key, 0)
            distribution.append({
                "mode": key,
                "name": name,
                "count": count,
                "percentage": round(count / max(grand_total, 1) * 100, 1),
            })
        
        # 按 RepairRecord 实时统计
        realtime_distribution = {}
        for item in distribution:
            realtime_distribution[item['mode']] = item['count']
        
        data = {
            "period": f"{start_date} 至 {end_date}",
            "total": grand_total,
            "distribution": distribution,
            "realtime": realtime_distribution,
        }
        
        return success_response(data=data, message="获取成功")
    
    except Exception as e:
        logger.error(f"[ModeDistribution] 获取模式分布失败: {e}", exc_info=True)
        return error_response(f"获取模式分布失败: {str(e)}", code=500)


# ============================================================
# 5. 平台分布
# ============================================================

@require_http_methods(["GET"])
@admin_required
def platform_distribution(request):
    """
    GET /api/stats/platform_distribution
    AI平台使用分布统计
    参数:
        - start: 开始日期 (可选)
        - end: 结束日期 (可选)
    """
    try:
        start_str = request.GET.get('start')
        end_str = request.GET.get('end')
        
        today_date = today()
        
        if start_str:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        else:
            start_date = today_date - timedelta(days=30)
        
        if end_str:
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        else:
            end_date = today_date
        
        # 从 DailyStats 汇总
        stats = DailyStats.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        
        platform_totals = {
            "baidu": sum(s.platform_baidu for s in stats),
            "tencent": sum(s.platform_tencent for s in stats),
            "replicate": sum(s.platform_replicate for s in stats),
        }
        
        grand_total = sum(platform_totals.values())
        
        platform_names = {
            "baidu": "百度AI",
            "tencent": "腾讯云",
            "replicate": "Replicate",
        }
        
        # 计算百分比
        distribution = []
        for key, name in platform_names.items():
            count = platform_totals.get(key, 0)
            distribution.append({
                "platform": key,
                "name": name,
                "count": count,
                "percentage": round(count / max(grand_total, 1) * 100, 1),
            })
        
        data = {
            "period": f"{start_date} 至 {end_date}",
            "total": grand_total,
            "distribution": distribution,
        }
        
        return success_response(data=data, message="获取成功")
    
    except Exception as e:
        logger.error(f"[PlatformDistribution] 获取平台分布失败: {e}", exc_info=True)
        return error_response(f"获取平台分布失败: {str(e)}", code=500)
